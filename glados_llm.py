"""
LLM routing for Glados — OpenClaw gateway (default) or direct Ollama.

OpenClaw exposes an OpenAI-compatible API on the gateway port (default 18789):
  POST /v1/chat/completions  — chat + vision (via x-openclaw-model when needed)
  POST /v1/embeddings        — memory vectors (agent memorySearch provider)

Enable chat completions in ~/.openclaw/openclaw.json:

  gateway.http.endpoints.chatCompletions.enabled: true
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence

from openai import OpenAI

OPENCLAW_DEFAULT_URL = "http://127.0.0.1:18789/v1"
OPENCLAW_DEFAULT_MODEL = "openclaw/default"


def _openclaw_config_path(cfg: Dict[str, Any]) -> str:
    explicit = str(cfg.get("openclaw_config_path") or "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    return os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")


def resolve_openclaw_token(cfg: Dict[str, Any]) -> str:
    """Gateway bearer token: env → glados.yaml → ~/.openclaw/openclaw.json."""
    for key in ("OPENCLAW_GATEWAY_TOKEN", "OPENCLAW_API_KEY"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    yaml_key = str(cfg.get("openclaw_api_key") or "").strip()
    if yaml_key:
        return yaml_key
    path = _openclaw_config_path(cfg)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return str((data.get("gateway") or {}).get("auth", {}).get("token") or "").strip()
    except Exception:
        return ""


def llm_provider(cfg: Dict[str, Any]) -> str:
    return str(cfg.get("llm_provider") or "openclaw").strip().lower()


def is_openclaw(cfg: Dict[str, Any]) -> bool:
    return llm_provider(cfg) in ("openclaw", "open-claw", "claw")


def resolve_llm_base_url(cfg: Dict[str, Any]) -> str:
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_base_url") or OPENCLAW_DEFAULT_URL).rstrip("/")
    return str(cfg.get("ollama_base_url") or "http://127.0.0.1:11434/v1").rstrip("/")


def resolve_chat_model(cfg: Dict[str, Any]) -> str:
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_model") or cfg.get("model_name") or OPENCLAW_DEFAULT_MODEL)
    return str(cfg.get("model_name") or "llama3.2:1b")


def resolve_vision_model(cfg: Dict[str, Any]) -> str:
    """Agent target for screen analysis — always routed through the active provider."""
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_vision_model") or cfg.get("vision_model") or OPENCLAW_DEFAULT_MODEL)
    return str(cfg.get("vision_model") or "llama3.2-vision")


def resolve_vision_backend_model(cfg: Dict[str, Any]) -> str:
    """Optional backend override sent as x-openclaw-model (e.g. openrouter/... vision model)."""
    if not is_openclaw(cfg):
        return ""
    return str(cfg.get("openclaw_vision_backend") or "").strip()


def resolve_embedding_model(cfg: Dict[str, Any]) -> str:
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_embedding_model") or cfg.get("embedding_model") or OPENCLAW_DEFAULT_MODEL)
    return str(cfg.get("embedding_model") or "nomic-embed-text")


def use_openclaw_embeddings(cfg: Dict[str, Any]) -> bool:
    backend = str(cfg.get("embedding_backend") or "").strip().lower()
    if backend in ("openclaw", "open-claw", "claw"):
        return True
    return is_openclaw(cfg) and backend not in ("ollama",)


def openclaw_extra_headers(cfg: Dict[str, Any], backend_model: str = "") -> Dict[str, str]:
    """Headers for x-openclaw-model backend overrides on shared-secret gateway auth."""
    if not is_openclaw(cfg):
        return {}
    override = (backend_model or "").strip()
    if not override:
        return {}
    return {"x-openclaw-model": override}


def resolve_api_key(cfg: Dict[str, Any]) -> str:
    if is_openclaw(cfg):
        token = resolve_openclaw_token(cfg)
        if token:
            return token
        return "openclaw"
    return "ollama"


def create_llm_client(cfg: Dict[str, Any]) -> OpenAI:
    return OpenAI(api_key=resolve_api_key(cfg), base_url=resolve_llm_base_url(cfg))


def completion_kwargs(cfg: Dict[str, Any], *, backend_model: str = "") -> Dict[str, Any]:
    kw: Dict[str, Any] = {}
    max_tok = int(cfg.get("llm_max_tokens") or 0)
    if max_tok > 0:
        kw["max_tokens"] = max_tok
    headers = openclaw_extra_headers(cfg, backend_model)
    if headers:
        kw["extra_headers"] = headers
    if not is_openclaw(cfg):
        keep = str(cfg.get("ollama_keep_alive") or "").strip()
        if keep:
            kw["extra_body"] = {"keep_alive": keep}
    return kw


def embed_texts(
    cfg: Dict[str, Any],
    texts: Sequence[str],
    *,
    client: Optional[OpenAI] = None,
) -> List[Optional[List[float]]]:
    """Embed via OpenClaw /v1/embeddings or direct Ollama native API."""
    if use_openclaw_embeddings(cfg):
        llm = client or create_llm_client(cfg)
        model = resolve_embedding_model(cfg)
        backend = str(cfg.get("openclaw_embedding_backend") or "").strip()
        headers = openclaw_extra_headers(cfg, backend)
        out: List[Optional[List[float]]] = []
        for text in texts:
            if not text:
                out.append(None)
                continue
            try:
                r = llm.embeddings.create(
                    model=model,
                    input=text,
                    extra_headers=headers or None,
                )
                vec = r.data[0].embedding
                out.append([float(x) for x in vec] if vec else None)
            except Exception:
                out.append(None)
        return out

    # Legacy direct Ollama embeddings (embedding_backend: ollama + llm_provider: ollama)
    import requests

    base = str(cfg.get("ollama_base_url") or "http://127.0.0.1:11434/v1").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    model = resolve_embedding_model(cfg)
    out = []
    for text in texts:
        if not text:
            out.append(None)
            continue
        try:
            resp = requests.post(
                f"{base}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=20,
            )
            if resp.status_code != 200:
                out.append(None)
                continue
            emb = (resp.json() or {}).get("embedding")
            out.append([float(x) for x in emb] if isinstance(emb, list) and emb else None)
        except Exception:
            out.append(None)
    return out


def check_llm_reachable(cfg: Dict[str, Any], timeout: float = 6.0) -> tuple[bool, str]:
    """Quick health check for startup banner."""
    import requests

    base = resolve_llm_base_url(cfg)
    headers: Dict[str, str] = {}
    if is_openclaw(cfg):
        token = resolve_openclaw_token(cfg)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"{base.rstrip('/')}/models"
    else:
        root = base.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        url = f"{root}/api/tags"

    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            provider = "OpenClaw" if is_openclaw(cfg) else "Ollama"
            model = resolve_chat_model(cfg)
            return True, f"{provider} OK @ {base} (model: {model})"
        if is_openclaw(cfg) and r.status_code == 404:
            return False, (
                "OpenClaw gateway is up but /v1/chat/completions may be disabled. "
                "Set gateway.http.endpoints.chatCompletions.enabled to true in "
                "~/.openclaw/openclaw.json and restart the gateway."
            )
        return False, f"LLM probe HTTP {r.status_code} @ {url}"
    except Exception as e:
        return False, f"LLM unreachable @ {base}: {e}"
