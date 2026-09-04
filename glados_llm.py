"""
LLM routing for Glados — Hermes llama.cpp (default), OpenRouter, OpenClaw, Ollama, or NVIDIA NIM.

Hermes:    local Hermes Agent llama-server (OpenAI /v1, native tool-calling)
NVIDIA:    integrate.api.nvidia.com/v1 with quad-key load balancer + local failover
OpenRouter: OpenAI-compatible API at https://openrouter.ai/api/v1
OpenClaw:    gateway on port 18789 with optional x-openclaw-model backend overrides
Ollama:      local http://127.0.0.1:11434/v1 (or deepseek-moe cluster)
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from openai import OpenAI

OPENCLAW_DEFAULT_URL = "http://127.0.0.1:18789/v1"
OPENCLAW_DEFAULT_MODEL = "openclaw/default"
OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1"
OPENROUTER_DEFAULT_MODEL = "openai/gpt-oss-120b:free"
NVIDIA_DEFAULT_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"


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
    return str(cfg.get("llm_provider") or "hermes").strip().lower()


def is_hermes(cfg: Dict[str, Any]) -> bool:
    return llm_provider(cfg) in (
        "hermes",
        "llamacpp",
        "llama.cpp",
        "llama-cpp",
        "hermes_local",
    )


def is_nvidia(cfg: Dict[str, Any]) -> bool:
    return llm_provider(cfg) in ("nvidia", "nim", "nvidia_nim", "nvcf")


def is_openrouter(cfg: Dict[str, Any]) -> bool:
    return llm_provider(cfg) in ("openrouter", "open-router")


def is_openclaw(cfg: Dict[str, Any]) -> bool:
    return llm_provider(cfg) in ("openclaw", "open-claw", "claw")


def is_ollama(cfg: Dict[str, Any]) -> bool:
    return llm_provider(cfg) in ("ollama", "local")


def is_llm_connection_error(exc: BaseException) -> bool:
    """True when llama.cpp / OpenAI never accepted the TCP connection."""
    name = type(exc).__name__
    if name in ("APIConnectionError", "ConnectError", "ConnectTimeout", "NewConnectionError"):
        return True
    text = str(exc).lower()
    needles = (
        "10061",
        "10060",
        "actively refused",
        "connection refused",
        "connection error",
        "connecterror",
        "failed to establish a new connection",
        "max retries exceeded",
        "name or service not known",
        "nodename nor servname",
    )
    return any(n in text for n in needles)


def llm_offline_speak(cfg: Optional[Dict[str, Any]] = None) -> str:
    """Short spoken line when the configured chat model is down."""
    cfg = cfg or {}
    if is_hermes(cfg):
        return (
            "Hermes llama-server is not running. Open Hermes Agent so the local "
            "model is listening on port 18434, then ask me again."
        )
    return "The language model is unreachable. Start it, then try again."


def llm_provider_label(cfg: Dict[str, Any]) -> str:
    if is_hermes(cfg):
        return "Hermes (local llama.cpp)"
    if is_nvidia(cfg):
        return "NVIDIA NIM"
    if is_openrouter(cfg):
        return "OpenRouter"
    if is_openclaw(cfg):
        return "OpenClaw"
    return "Ollama"


def resolve_openrouter_api_key(cfg: Dict[str, Any]) -> str:
    for key in ("OPENROUTER_API_KEY",):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return str(cfg.get("openrouter_api_key") or "").strip()


def resolve_nvidia_api_key(cfg: Dict[str, Any]) -> str:
    for key in (
        "NVIDIA_API_KEY_1",
        "NVIDIA_API_KEY",
        "NVIDIA_API_KEY_2",
        "NVIDIA_API_KEY_3",
        "NVIDIA_API_KEY_4",
    ):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    keys = cfg.get("nvidia_api_keys") or []
    if isinstance(keys, list) and keys:
        return str(keys[0]).strip()
    return str(cfg.get("nvidia_api_key") or "").strip()


def resolve_llm_base_url(cfg: Dict[str, Any]) -> str:
    if is_hermes(cfg):
        from glados_llm_hermes import discover_hermes_endpoint

        return discover_hermes_endpoint(cfg)["base_url"]
    if is_nvidia(cfg):
        return str(cfg.get("nvidia_base_url") or NVIDIA_DEFAULT_URL).rstrip("/")
    if is_openrouter(cfg):
        return str(cfg.get("openrouter_base_url") or OPENROUTER_DEFAULT_URL).rstrip("/")
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_base_url") or OPENCLAW_DEFAULT_URL).rstrip("/")
    return str(cfg.get("ollama_base_url") or "http://127.0.0.1:11434/v1").rstrip("/")


def resolve_chat_model(cfg: Dict[str, Any]) -> str:
    if is_hermes(cfg):
        from glados_llm_hermes import discover_hermes_endpoint

        return discover_hermes_endpoint(cfg)["model"]
    if is_nvidia(cfg):
        try:
            from glados_llm_nvidia import resolve_nvidia_chat_model

            return resolve_nvidia_chat_model(cfg)
        except Exception:
            return str(
                cfg.get("model_name") or cfg.get("nvidia_model") or NVIDIA_DEFAULT_MODEL
            )
    if is_openrouter(cfg):
        raw = str(cfg.get("model_name") or cfg.get("openrouter_model") or "").strip()
        if raw and not raw.startswith("openclaw/"):
            return raw
        return OPENROUTER_DEFAULT_MODEL
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_model") or cfg.get("model_name") or OPENCLAW_DEFAULT_MODEL)
    return str(cfg.get("model_name") or "llama3.2:1b")


def resolve_vision_model(cfg: Dict[str, Any]) -> str:
    """Agent target for screen analysis — routed through the active provider."""
    if is_hermes(cfg):
        return str(cfg.get("vision_model") or resolve_chat_model(cfg))
    if is_nvidia(cfg):
        return str(cfg.get("vision_model") or cfg.get("nvidia_vision_model") or resolve_chat_model(cfg))
    if is_openrouter(cfg):
        return str(cfg.get("vision_model") or cfg.get("openrouter_vision_model") or resolve_chat_model(cfg))
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_vision_model") or cfg.get("vision_model") or OPENCLAW_DEFAULT_MODEL)
    return str(cfg.get("vision_model") or "llama3.2-vision")


def resolve_vision_backend_model(cfg: Dict[str, Any]) -> str:
    """Optional backend override sent as x-openclaw-model (e.g. openrouter/... vision model)."""
    if not is_openclaw(cfg):
        return ""
    return str(cfg.get("openclaw_vision_backend") or "").strip()


def resolve_embedding_model(cfg: Dict[str, Any]) -> str:
    backend = str(cfg.get("embedding_backend") or "").strip().lower()
    if is_hermes(cfg) or backend in ("none", "off", ""):
        if is_hermes(cfg) and backend not in ("nvidia", "nim", "openrouter", "openclaw"):
            return str(cfg.get("embedding_model") or "nomic-embed-text")
    if (is_nvidia(cfg) or backend in ("nvidia", "nim")) and not is_hermes(cfg):
        return str(cfg.get("embedding_model") or "nvidia/nv-embedqa-e5-v5")
    if is_openrouter(cfg) or backend in ("openrouter", "open-router"):
        return str(cfg.get("embedding_model") or "openai/text-embedding-3-small")
    if is_openclaw(cfg):
        return str(cfg.get("openclaw_embedding_model") or cfg.get("embedding_model") or OPENCLAW_DEFAULT_MODEL)
    return str(cfg.get("embedding_model") or "nomic-embed-text")


def use_nvidia_embeddings(cfg: Dict[str, Any]) -> bool:
    if is_hermes(cfg):
        return False
    backend = str(cfg.get("embedding_backend") or "").strip().lower()
    if backend in ("nvidia", "nim"):
        return is_nvidia(cfg)
    return is_nvidia(cfg) and backend not in ("ollama", "openclaw", "open-claw", "claw", "openrouter", "none", "off")


def use_openrouter_embeddings(cfg: Dict[str, Any]) -> bool:
    backend = str(cfg.get("embedding_backend") or "").strip().lower()
    if backend in ("openrouter", "open-router"):
        return True
    return is_openrouter(cfg) and backend not in ("ollama", "openclaw", "open-claw", "claw", "nvidia", "nim")


def use_openclaw_embeddings(cfg: Dict[str, Any]) -> bool:
    backend = str(cfg.get("embedding_backend") or "").strip().lower()
    if backend in ("openclaw", "open-claw", "claw"):
        return True
    return is_openclaw(cfg) and backend not in ("ollama", "openrouter", "open-router")


def openrouter_extra_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    referer = str(cfg.get("openrouter_http_referer") or cfg.get("brain_dashboard_url") or "").strip()
    title = str(cfg.get("openrouter_app_title") or "GLaDOS").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title
    return headers


def openclaw_extra_headers(cfg: Dict[str, Any], backend_model: str = "") -> Dict[str, str]:
    """Headers for x-openclaw-model backend overrides on shared-secret gateway auth."""
    if not is_openclaw(cfg):
        return {}
    override = (backend_model or "").strip()
    if not override:
        return {}
    return {"x-openclaw-model": override}


def resolve_api_key(cfg: Dict[str, Any]) -> str:
    if is_hermes(cfg):
        from glados_llm_hermes import discover_hermes_endpoint

        return discover_hermes_endpoint(cfg)["api_key"]
    if is_nvidia(cfg):
        key = resolve_nvidia_api_key(cfg)
        if key:
            return key
        return "missing-nvidia-key"
    if is_openrouter(cfg):
        key = resolve_openrouter_api_key(cfg)
        if key:
            return key
        return "missing-openrouter-key"
    if is_openclaw(cfg):
        token = resolve_openclaw_token(cfg)
        if token:
            return token
        return "openclaw"
    return "ollama"


def _is_rate_limit_error(exc: BaseException) -> bool:
    """True when an API error indicates HTTP 429 / provider rate limiting."""
    if getattr(exc, "status_code", None) == 429:
        return True
    error_str = str(exc)
    return "429" in error_str or "rate_limit" in error_str.lower()


# --- Local Ollama fallback shim (Phase 4) ---------------------------------
# Mimics the OpenAI chat.completions response object so downstream swarm code
# (response.choices[0].message.content / .tool_calls) works unchanged.
class _ShimFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _ShimToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.type = "function"
        self.function = _ShimFunction(name, arguments)


class _ShimMessage:
    def __init__(self, content: str, tool_calls: Optional[List[Any]] = None) -> None:
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or None


class _ShimChoice:
    def __init__(self, message: "_ShimMessage") -> None:
        self.message = message
        self.finish_reason = "stop"


class _ShimResponse:
    def __init__(self, message: "_ShimMessage") -> None:
        self.choices = [_ShimChoice(message)]
        self.model = "ollama-fallback"


def _ollama_fallback(
    cfg: Dict[str, Any],
    kwargs: Dict[str, Any],
    on_local_fallback: Optional[Callable[[], None]] = None,
) -> Optional[Any]:
    """Reroute the exact same payload to a local Ollama instance on 429 exhaustion."""
    import uuid

    import requests

    if not bool(cfg.get("ollama_fallback_enabled", True)):
        return None
    messages = kwargs.get("messages")
    if not messages:
        return None

    url = str(cfg.get("ollama_fallback_url") or "http://localhost:11434/api/chat")
    model = str(cfg.get("ollama_fallback_model") or "llama3.2:1b")

    if on_local_fallback:
        try:
            on_local_fallback()
        except Exception:
            pass
    print("[SYSTEM] Cloud API locked. Rerouting neural pathways to local hardware (Ollama).")

    payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    tools = kwargs.get("tools")
    if tools:
        payload["tools"] = tools
    max_tok = kwargs.get("max_tokens")
    if max_tok:
        payload["options"] = {"num_predict": int(max_tok)}

    try:
        resp = requests.post(url, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise Exception(f"Local Ollama fallback failed: {e}")

    msg = data.get("message") or {}
    content = str(msg.get("content") or "")

    tool_calls: Optional[List[Any]] = None
    raw_calls = msg.get("tool_calls") or []
    if raw_calls:
        tool_calls = []
        for c in raw_calls:
            fn = (c or {}).get("function") or {}
            name = str(fn.get("name") or "")
            arguments = fn.get("arguments")
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments or {})
            tool_calls.append(
                _ShimToolCall(f"ollama-{uuid.uuid4().hex[:8]}", name, arguments)
            )

    return _ShimResponse(_ShimMessage(content, tool_calls))


def call_openrouter_with_retry(
    client: Any,
    *args: Any,
    cfg: Optional[Dict[str, Any]] = None,
    on_rate_limit_retry: Optional[Callable[[int], None]] = None,
    on_local_fallback: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """
    chat.completions.create with exponential backoff on OpenRouter 429s.

    Retries: 3s, 6s, 12s (3 attempts total). If the rate limit persists after
    the final retry, reroute the same payload to a local Ollama instance
    (Phase 4) instead of crashing the agent.
    """
    max_retries = 3
    base_delay = 3  # seconds

    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(*args, **kwargs)
        except Exception as e:
            if _is_rate_limit_error(e):
                if attempt < max_retries - 1:
                    sleep_time = base_delay * (2**attempt)
                    print(
                        f"[SYSTEM] OpenRouter Rate Limit hit. "
                        f"Agent pausing for {sleep_time}s before retry..."
                    )
                    if on_rate_limit_retry:
                        try:
                            on_rate_limit_retry(sleep_time)
                        except Exception:
                            pass
                    time.sleep(sleep_time)
                else:
                    fallback = _ollama_fallback(cfg or {}, kwargs, on_local_fallback)
                    if fallback is not None:
                        return fallback
                    raise Exception(
                        f"Agent failed after {max_retries} retries due to strict rate limits."
                    ) from e
            else:
                raise


def create_llm_client(cfg: Dict[str, Any]) -> Union[OpenAI, Any]:
    """Return an OpenAI client (Hermes llama.cpp, NVIDIA balancer, or other)."""
    if is_hermes(cfg):
        from glados_llm_hermes import create_hermes_client

        return create_hermes_client(cfg)
    if is_nvidia(cfg):
        from glados_llm_nvidia import create_nvidia_balanced_client

        lb = create_nvidia_balanced_client(cfg)
        lb.sync_openai_env()
        if hasattr(lb, "sync_interpreter_env"):
            lb.sync_interpreter_env()
        return lb
    default_headers = openrouter_extra_headers(cfg) if is_openrouter(cfg) else None
    return OpenAI(
        api_key=resolve_api_key(cfg),
        base_url=resolve_llm_base_url(cfg),
        default_headers=default_headers or None,
    )


def sync_llm_runtime_env(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Set OPENAI_* so Open Interpreter uses the same brain as chat."""
    if is_hermes(cfg):
        from glados_llm_hermes import sync_hermes_env

        return sync_hermes_env(cfg=cfg)
    if is_nvidia(cfg):
        from glados_llm_nvidia import create_nvidia_balanced_client

        lb = create_nvidia_balanced_client(cfg)
        primary = lb.sync_openai_env()
        if hasattr(lb, "sync_interpreter_env"):
            lb.sync_interpreter_env()
        return dict(primary)
    ep = {
        "name": llm_provider(cfg),
        "kind": llm_provider(cfg),
        "api_key": resolve_api_key(cfg),
        "base_url": resolve_llm_base_url(cfg),
        "model": resolve_chat_model(cfg),
    }
    os.environ["OPENAI_API_KEY"] = ep["api_key"]
    os.environ["OPENAI_API_BASE"] = ep["base_url"]
    os.environ["OPENAI_BASE_URL"] = ep["base_url"]
    os.environ["OPENAI_MODEL_NAME"] = ep["model"]
    return ep


def completion_kwargs(cfg: Dict[str, Any], *, backend_model: str = "") -> Dict[str, Any]:
    kw: Dict[str, Any] = {}
    max_tok = int(cfg.get("llm_max_tokens") or 0)
    if max_tok > 0:
        kw["max_tokens"] = max_tok
    if is_hermes(cfg):
        extra = dict(kw.get("extra_body") or {})
        extra.setdefault("chat_template_kwargs", {"enable_thinking": True})
        kw["extra_body"] = extra
        return kw
    if is_openrouter(cfg):
        headers = openrouter_extra_headers(cfg)
        if headers:
            kw["extra_headers"] = headers
        return kw
    headers = openclaw_extra_headers(cfg, backend_model)
    if headers:
        kw["extra_headers"] = headers
    if is_ollama(cfg):
        keep = str(cfg.get("ollama_keep_alive") or "").strip()
        if keep:
            body = dict(kw.get("extra_body") or {})
            body["keep_alive"] = keep
            kw["extra_body"] = body
    return kw


def embed_texts(
    cfg: Dict[str, Any],
    texts: Sequence[str],
    *,
    client: Optional[Any] = None,
) -> List[Optional[List[float]]]:
    """Embed via NVIDIA, OpenRouter, OpenClaw /v1/embeddings, or direct Ollama native API."""
    if use_nvidia_embeddings(cfg) or use_openrouter_embeddings(cfg):
        llm = client or create_llm_client(cfg)
        model = resolve_embedding_model(cfg)
        out: List[Optional[List[float]]] = []
        for text in texts:
            if not text:
                out.append(None)
                continue
            try:
                r = llm.embeddings.create(model=model, input=text)
                vec = r.data[0].embedding
                out.append([float(x) for x in vec] if vec else None)
            except Exception:
                out.append(None)
        return out

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
    if is_hermes(cfg):
        key = resolve_api_key(cfg)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        url = f"{base.rstrip('/')}/models"
    elif is_nvidia(cfg):
        key = resolve_nvidia_api_key(cfg)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        url = f"{base.rstrip('/')}/models"
    elif is_openrouter(cfg):
        key = resolve_openrouter_api_key(cfg)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        headers.update(openrouter_extra_headers(cfg))
        url = f"{base.rstrip('/')}/models"
    elif is_openclaw(cfg):
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
            provider = llm_provider_label(cfg)
            model = resolve_chat_model(cfg)
            extra = ""
            if is_nvidia(cfg):
                from glados_llm_nvidia import build_endpoints

                eps = build_endpoints(cfg)
                n_cloud = sum(1 for e in eps if e.get("kind") == "nvidia")
                extra = f" | keys={n_cloud} + local failover"
            return True, f"{provider} OK @ {base} (model: {model}{extra})"
        if is_hermes(cfg) and r.status_code in (401, 403):
            return False, (
                "Hermes llama.cpp rejected the API key. Leave Hermes Agent running "
                "so GLaDOS can read runtimes/llamacpp/server.json."
            )
        if is_nvidia(cfg) and r.status_code in (401, 403):
            return False, (
                "NVIDIA rejected the API key. Set NVIDIA_API_KEY_1..4 in .env "
                "(never commit keys)."
            )
        if is_openclaw(cfg) and r.status_code == 404:
            return False, (
                "OpenClaw gateway is up but /v1/chat/completions may be disabled. "
                "Set gateway.http.endpoints.chatCompletions.enabled to true in "
                "~/.openclaw/openclaw.json and restart the gateway."
            )
        if is_openrouter(cfg) and r.status_code in (401, 403):
            return False, (
                "OpenRouter rejected the API key. Set OPENROUTER_API_KEY env or "
                "openrouter_api_key in configs/glados.yaml."
            )
        return False, f"LLM probe HTTP {r.status_code} @ {url}"
    except Exception as e:
        if is_hermes(cfg):
            return False, (
                f"Hermes llama-server is not listening @ {base}. "
                "Open Hermes Agent first (local llama.cpp on port 18434), "
                "then start GLaDOS with only the venv tray_launcher."
            )
        return False, f"LLM unreachable @ {base}: {e}"
