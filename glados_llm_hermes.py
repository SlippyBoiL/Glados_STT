"""Local Hermes Agent llama.cpp (OpenAI-compatible) — GLaDOS chat + tool-calling.

Reads the managed llama-server from Hermes Agent state (port 18434 by default).
Never logs API keys. Do not bind this server to port 8000 (Honcho).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_HERMES_BASE = "http://127.0.0.1:18434/v1"
DEFAULT_HERMES_MODEL = "Qwen3.6-35B-A3B-UD-Q4_K_M"


def hermes_home() -> Path:
    explicit = (os.environ.get("HERMES_HOME") or "").strip()
    if explicit:
        return Path(explicit)
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME") or "."
    return Path(local) / "hermes"


def _server_state_path() -> Path:
    return hermes_home() / "runtimes" / "llamacpp" / "server.json"


def _hermes_config_path() -> Path:
    return hermes_home() / "config.yaml"


def _read_server_state() -> Dict[str, str]:
    path = _server_state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    base = str(data.get("base_url") or "").strip()
    key = str(data.get("api_key") or "").strip()
    if base:
        out["base_url"] = base.rstrip("/")
    if key:
        out["api_key"] = key
    return out


def _read_hermes_config_model() -> str:
    path = _hermes_config_path()
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    in_model = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("model:") and ":" in line[6:]:
            # model: { default: ... } unlikely in this yaml
            in_model = True
            continue
        if line.startswith("model:"):
            in_model = True
            continue
        if in_model and line[:1] not in (" ", "\t"):
            break
        if in_model:
            stripped = line.strip()
            if stripped.startswith("default:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                return val
    return ""


def discover_hermes_endpoint(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Resolve llama.cpp OpenAI root, key, and model id (no secrets in return logs)."""
    cfg = cfg or {}
    state = _read_server_state()

    base = (
        str(cfg.get("hermes_base_url") or "").strip()
        or (os.environ.get("HERMES_BASE_URL") or "").strip()
        or state.get("base_url")
        or DEFAULT_HERMES_BASE
    ).rstrip("/")
    key = (
        str(cfg.get("hermes_api_key") or "").strip()
        or (os.environ.get("HERMES_API_KEY") or "").strip()
        or state.get("api_key")
        or ""
    )
    model = (
        str(cfg.get("hermes_model") or "").strip()
        or (os.environ.get("HERMES_MODEL") or "").strip()
        or _read_hermes_config_model()
        or DEFAULT_HERMES_MODEL
    )
    return {
        "name": "hermes-llamacpp",
        "kind": "hermes",
        "api_key": key or "sk-no-key-required",
        "base_url": base,
        "model": model,
    }


def sync_hermes_env(endpoint: Optional[Dict[str, str]] = None, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Point OpenAI / Open Interpreter env at the local Hermes server."""
    ep = endpoint or discover_hermes_endpoint(cfg)
    os.environ["OPENAI_API_KEY"] = ep["api_key"]
    os.environ["OPENAI_API_BASE"] = ep["base_url"]
    os.environ["OPENAI_BASE_URL"] = ep["base_url"]
    os.environ["OPENAI_MODEL_NAME"] = ep["model"]
    os.environ["GLADOS_LLM_FUNCTIONS"] = "1"
    return dict(ep)


def create_hermes_client(cfg: Optional[Dict[str, Any]] = None):
    from openai import OpenAI

    ep = discover_hermes_endpoint(cfg)
    sync_hermes_env(ep)
    return OpenAI(api_key=ep["api_key"], base_url=ep["base_url"])
