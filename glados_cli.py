#!/usr/bin/env python3
"""
OpenJarvis-inspired CLI: `doctor` (diagnostics), `ask` (one-shot local LLM), `init` (setup hints).
Does not replace KernelLamma — same stack, same Ollama endpoint.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from urllib.parse import urlparse

# Repo root = directory containing this file
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from glados_config import CONFIG_PATH, load_config


def _ollama_api_root(cfg: dict) -> str:
    base = cfg["ollama_base_url"].rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    return base


def _ollama_installed_models(cfg: dict) -> list:
    import json
    import urllib.request

    root = _ollama_api_root(cfg)
    try:
        req = urllib.request.Request(f"{root}/api/tags", headers={"User-Agent": "GladosCLI"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _model_is_available(want: str, installed: list) -> bool:
    if not want or not installed:
        return False
    for name in installed:
        if name == want or name.startswith(want + ":"):
            return True
    return False


def cmd_doctor() -> int:
    cfg = load_config()
    root = _ollama_api_root(cfg)

    print("[*] Glados doctor (local-first checks)\n")

    ok = True
    try:
        import urllib.request
        req = urllib.request.Request(f"{root}/api/tags", headers={"User-Agent": "GladosDoctor"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        print(f"  [OK] Ollama reachable: {root}/api/tags")
        installed = _ollama_installed_models(cfg)
        want = cfg.get("model_name", "")
        if want and installed:
            if _model_is_available(want, installed):
                print(f"  [OK] Configured model '{want}' is installed.")
            else:
                print(f"  [FAIL] Model '{want}' not installed. On this machine you have: {', '.join(installed)}")
                print(f"         Run: ollama pull {want}")
                print("         Or set model_name in configs/glados.yaml to one of the names above.")
                ok = False
        elif want and not installed:
            print(f"  [!] No models in Ollama — run: ollama pull {want}")
            ok = False
        host = (urlparse(root).hostname or "").lower()
        if host not in ("localhost", "127.0.0.1", "::1"):
            print(
                f"  [i] Ollama runs on '{host}' — the GPU that matters is on *that* machine, not necessarily this PC."
            )
        else:
            print(
                "  [i] Local Ollama: if the model is slow and GPU stays idle, update GPU drivers, run `ollama ps`, "
                "and check Task Manager / `nvidia-smi` while a request runs."
            )
    except Exception as e:
        print(f"  [FAIL] Ollama not reachable at {root}: {e}")
        ok = False
    piper = shutil.which("piper")
    if piper:
        print(f"  [OK] piper on PATH: {piper}")
    else:
        print("  [FAIL] piper not found on PATH")
        ok = False

    pm = cfg.get("piper_model_path", "")
    if pm and os.path.isfile(pm):
        print(f"  [OK] Piper voice model: {pm}")
    else:
        print(f"  [FAIL] Piper model missing: {pm}")
        ok = False

    plug = os.path.join(REPO_ROOT, cfg.get("plugins_dir", "plugins"))
    if os.path.isdir(plug):
        print(f"  [OK] plugins directory: {plug}")
    else:
        print(f"  [FAIL] plugins directory missing: {plug}")
        ok = False

    if os.path.isfile(CONFIG_PATH):
        print(f"  [OK] config file: {CONFIG_PATH}")
    else:
        print(f"  [!] config file not found (optional): {CONFIG_PATH}")

    try:
        import chromadb  # noqa: F401
        print("  [OK] ChromaDB import (shared swarm brain)")
    except Exception as e:
        print(f"  [!] ChromaDB: {e} (needed for the unified swarm memory)")

    print()
    return 0 if ok else 1


def cmd_init() -> int:
    cfg = load_config()
    print("[*] Glados init — suggested steps (like `jarvis init`, but for this repo)\n")
    print("  1. Install Ollama and run: ollama serve")
    print(f"  2. Pull models: ollama pull {cfg['model_name']}")
    print(f"     (vision) ollama pull {cfg.get('vision_model', 'llama3.2-vision')}")
    print("  3. Install Piper and place glados.onnx in the repo root (or set PIPER_MODEL_PATH).")
    print(f"  4. Edit configs/glados.yaml or set OLLAMA_BASE_URL / MODEL_NAME (current: {cfg['ollama_base_url']}).")
    print("  5. Run: py glados_cli.py doctor")
    print("  6. Start the assistant: py KernelLamma.py")
    print("  7. Auto-restart on save: pip install watchdog && py run_watch.py\n")
    return 0


GLADOS_ASK_SYSTEM = (
    "You are GLaDOS (Aperture Science). Answer in one or two sentences. "
    "Cold, clinical sarcasm. No emojis. If asked something trivial, mock the test subject."
)


def cmd_ask(question: str) -> int:
    cfg = load_config()
    try:
        from glados_llm import create_llm_client, resolve_chat_model, completion_kwargs, is_openclaw
    except ImportError:
        print("[!] glados_llm / openai package required.")
        return 1

    client = create_llm_client(cfg)
    model = resolve_chat_model(cfg)
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GLADOS_ASK_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0.7,
            **completion_kwargs(cfg),
        )
        text = (r.choices[0].message.content or "").strip()
        print(text)
        return 0
    except Exception as e:
        if not is_openclaw(cfg):
            installed = _ollama_installed_models(cfg)
            want = cfg.get("model_name", "")
            code = getattr(e, "status_code", None)
            err_txt = str(e).lower()
            if code == 404 or "not found" in err_txt or "404" in str(e):
                print(f"[!] Model '{want}' is not available on this Ollama server (404).")
                print(f"    On the machine running Ollama, run: ollama pull {want}")
                if installed:
                    print(f"    Models already installed there: {', '.join(installed)}")
                    print("    Or set model_name in configs/glados.yaml (or MODEL_NAME) to one of those names.")
                else:
                    print("    Ollama reported no models — pull any model you want to use first.")
                return 1
        print(f"[!] ask failed: {e}")
        return 1


def main() -> int:
    p = argparse.ArgumentParser(prog="glados", description="Glados local-first CLI (OpenJarvis-style helpers)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Check Ollama, Piper, plugins, config")
    sub.add_parser("init", help="Print setup steps")
    ask_p = sub.add_parser("ask", help='One-shot question (like jarvis ask "..." )')
    ask_p.add_argument("question", nargs=argparse.REMAINDER, help="Question text")

    args = p.parse_args()
    if args.cmd == "doctor":
        return cmd_doctor()
    if args.cmd == "init":
        return cmd_init()
    if args.cmd == "ask":
        q = " ".join(args.question).strip()
        if not q:
            print("[!] Usage: glados ask What is 2+2?")
            return 1
        return cmd_ask(q)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
