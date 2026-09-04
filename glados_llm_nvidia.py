"""
NVIDIA NIM Quad-Key Load Balancer — OpenAI-compatible client with key rotation
and local deepseek-moe cluster failover.
"""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Callable, Dict, List, Optional, Sequence

import httpx
from openai import OpenAI

NVIDIA_DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
# Nous Hermes — tool-calling specialist. NIM may or may not list these; we probe.
HERMES_NIM_CANDIDATES = (
    "nousresearch/hermes-3-llama-3.1-70b-instruct",
    "nousresearch/hermes-3-llama-3.1-405b-instruct",
    "nousresearch/hermes-3-llama-3.1-8b-instruct",
    "nousresearch/hermes-2-pro-llama-3-8b",
)
HERMES_OPENROUTER_MODEL = "nousresearch/hermes-3-llama-3.1-70b"
OPENROUTER_DEFAULT_BASE = "https://openrouter.ai/api/v1"
# Per-key defaults when NVIDIA_MODEL_N / nvidia_endpoint_models is unset
NVIDIA_KEY_MODELS = (
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",  # key 1 — primary personality / chat
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",  # key 2 — failover
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",  # key 3 — failover
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",  # key 4 — spare
)
LOCAL_FALLBACK_BASE = "http://192.168.0.102:5000/v1"
LOCAL_FALLBACK_MODEL = "deepseek-moe"
# Hard ceiling so a hung NIM model cannot block the HUD forever.
LLM_CALL_HARD_TIMEOUT_SEC = 28.0

_NIM_MODEL_IDS: Optional[List[str]] = None
_NIM_MODEL_LOCK = threading.Lock()
_HERMES_RESOLVE_LOCK = threading.Lock()
_HERMES_RESOLVED: Optional[Dict[str, str]] = None


def _env_keys() -> List[str]:
    keys: List[str] = []
    for name in (
        "NVIDIA_API_KEY_1",
        "NVIDIA_API_KEY_2",
        "NVIDIA_API_KEY_3",
        "NVIDIA_API_KEY_4",
        "NVIDIA_API_KEY",
    ):
        val = (os.environ.get(name) or "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def _openrouter_key(cfg: Optional[Dict[str, Any]] = None) -> str:
    cfg = cfg or {}
    for name in ("OPENROUTER_API_KEY",):
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return str(cfg.get("openrouter_api_key") or "").strip()


def list_nim_model_ids(cfg: Optional[Dict[str, Any]] = None) -> List[str]:
    """Best-effort GET /v1/models on NVIDIA NIM. Cached for the process lifetime."""
    global _NIM_MODEL_IDS
    with _NIM_MODEL_LOCK:
        if _NIM_MODEL_IDS is not None:
            return list(_NIM_MODEL_IDS)
    cfg = cfg or {}
    keys = _env_keys()
    yaml_keys = cfg.get("nvidia_api_keys") or []
    if isinstance(yaml_keys, list):
        for k in yaml_keys:
            if k and str(k) not in keys:
                keys.append(str(k))
    api_key = keys[0] if keys else str(cfg.get("nvidia_api_key") or "").strip()
    if not api_key:
        with _NIM_MODEL_LOCK:
            _NIM_MODEL_IDS = []
        return []
    base = str(cfg.get("nvidia_base_url") or NVIDIA_DEFAULT_BASE).rstrip("/")
    ids: List[str] = []
    try:
        resp = httpx.get(
            f"{base}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=6.0,
        )
        if resp.status_code == 200:
            data = resp.json() or {}
            for item in data.get("data") or []:
                mid = str((item or {}).get("id") or "").strip()
                if mid:
                    ids.append(mid)
    except Exception:
        ids = []
    with _NIM_MODEL_LOCK:
        _NIM_MODEL_IDS = ids
    return list(ids)


def _hermes_match_on_nim(cfg: Optional[Dict[str, Any]] = None) -> str:
    ids = list_nim_model_ids(cfg)
    lower = {m.lower(): m for m in ids}
    extra = cfg.get("hermes_nim_candidates") if cfg else None
    candidates: List[str] = []
    if isinstance(extra, list):
        candidates.extend(str(x).strip() for x in extra if x)
    candidates.extend(HERMES_NIM_CANDIDATES)
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for mid in ids:
        if "hermes" in mid.lower() and "nous" in mid.lower():
            return mid
    for mid in ids:
        if "hermes" in mid.lower():
            return mid
    return ""


def resolve_hermes_route(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Pick the Hermes tool-calling model.

    Returns dict with keys: model, source (nvidia|openrouter|fallback), note
    """
    global _HERMES_RESOLVED
    with _HERMES_RESOLVE_LOCK:
        if _HERMES_RESOLVED is not None:
            return dict(_HERMES_RESOLVED)

    cfg = cfg or {}
    prefer = cfg.get("nvidia_prefer_hermes")
    if prefer is None:
        prefer = True
    if isinstance(prefer, str):
        prefer = prefer.strip().lower() in ("1", "true", "yes", "on")

    configured = str(
        cfg.get("nvidia_model") or cfg.get("model_name") or NVIDIA_DEFAULT_MODEL
    ).strip()
    if "hermes" in configured.lower():
        nim_ids = list_nim_model_ids(cfg)
        if not nim_ids or configured in nim_ids or configured.lower() in {m.lower() for m in nim_ids}:
            result = {"model": configured, "source": "nvidia", "note": "explicit Hermes model"}
        else:
            or_key = _openrouter_key(cfg)
            or_model = str(cfg.get("hermes_openrouter_model") or HERMES_OPENROUTER_MODEL)
            if or_key:
                result = {
                    "model": or_model,
                    "source": "openrouter",
                    "note": f"{configured} not on this NIM catalog; using OpenRouter Hermes",
                }
            else:
                result = {
                    "model": NVIDIA_DEFAULT_MODEL,
                    "source": "fallback",
                    "note": f"{configured} not on NIM and no OPENROUTER_API_KEY; staying on Nemotron",
                }
        with _HERMES_RESOLVE_LOCK:
            _HERMES_RESOLVED = result
        return dict(result)

    if not prefer:
        result = {"model": configured or NVIDIA_DEFAULT_MODEL, "source": "nvidia", "note": "hermes disabled"}
        with _HERMES_RESOLVE_LOCK:
            _HERMES_RESOLVED = result
        return dict(result)

    nim_hermes = _hermes_match_on_nim(cfg)
    if nim_hermes:
        result = {
            "model": nim_hermes,
            "source": "nvidia",
            "note": f"Hermes on NIM catalog: {nim_hermes}",
        }
        with _HERMES_RESOLVE_LOCK:
            _HERMES_RESOLVED = result
        print(f"[*] Hermes: using NVIDIA NIM model {nim_hermes}")
        return dict(result)

    or_key = _openrouter_key(cfg)
    or_model = str(cfg.get("hermes_openrouter_model") or HERMES_OPENROUTER_MODEL)
    if or_key:
        result = {
            "model": or_model,
            "source": "openrouter",
            "note": f"Hermes not on NIM catalog; primary = OpenRouter {or_model}",
        }
        with _HERMES_RESOLVE_LOCK:
            _HERMES_RESOLVED = result
        print(f"[*] Hermes: NIM catalog has no Hermes id; primary OpenRouter {or_model}")
        return dict(result)

    result = {
        "model": configured or NVIDIA_DEFAULT_MODEL,
        "source": "fallback",
        "note": (
            "Hermes 3 is not on this NVIDIA NIM catalog. "
            "Set OPENROUTER_API_KEY to use nousresearch/hermes-3-llama-3.1-70b, "
            f"or keep {configured or NVIDIA_DEFAULT_MODEL} as the agent model."
        ),
    }
    with _HERMES_RESOLVE_LOCK:
        _HERMES_RESOLVED = result
    print(f"[*] Hermes: {result['note']}")
    return dict(result)


def resolve_nvidia_chat_model(cfg: Optional[Dict[str, Any]] = None) -> str:
    """Model id the balancer will actually call for GLaDOS chat (NVIDIA, not OI)."""
    cfg = cfg or {}
    route = resolve_hermes_route(cfg)
    if route.get("source") == "nvidia":
        return route["model"]
    return str(cfg.get("nvidia_model") or cfg.get("model_name") or NVIDIA_DEFAULT_MODEL)


def _model_for_key_index(cfg: Dict[str, Any], index: int, fallback: str) -> str:
    """Resolve per-key NIM model: env NVIDIA_MODEL_N → yaml list → curated defaults."""
    env = (os.environ.get(f"NVIDIA_MODEL_{index + 1}") or "").strip()
    if env:
        return env
    yaml_models = cfg.get("nvidia_endpoint_models") or []
    if isinstance(yaml_models, str):
        yaml_models = [m.strip() for m in yaml_models.split(",") if m.strip()]
    if isinstance(yaml_models, list) and index < len(yaml_models) and yaml_models[index]:
        return str(yaml_models[index]).strip()
    if index < len(NVIDIA_KEY_MODELS):
        return NVIDIA_KEY_MODELS[index]
    return fallback


def build_endpoints(cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Build the ENDPOINTS routing table:
      1-N NVIDIA NIM keys (each with its own model)
      last: local deepseek-moe cluster failover
    """
    cfg = cfg or {}
    hermes = resolve_hermes_route(cfg)
    base = str(cfg.get("nvidia_base_url") or NVIDIA_DEFAULT_BASE).rstrip("/")
    default_model = str(
        cfg.get("nvidia_model") or cfg.get("model_name") or NVIDIA_DEFAULT_MODEL
    )
    yaml_keys = cfg.get("nvidia_api_keys") or []
    if isinstance(yaml_keys, str):
        yaml_keys = [k.strip() for k in yaml_keys.split(",") if k.strip()]

    keys = list(yaml_keys) if isinstance(yaml_keys, list) else []
    for k in _env_keys():
        if k not in keys:
            keys.append(k)

    endpoints: List[Dict[str, str]] = []
    for i, key in enumerate(keys):
        if not key or str(key).startswith("nvapi-YOUR"):
            continue
        model = (
            hermes["model"]
            if hermes.get("source") == "nvidia"
            else _model_for_key_index(cfg, i, default_model)
        )
        endpoints.append(
            {
                "name": f"nvidia-{i + 1}",
                "api_key": str(key).strip(),
                "base_url": base,
                "model": model,
                "kind": "nvidia",
            }
        )

    if hermes.get("source") == "openrouter":
        or_key = _openrouter_key(cfg)
        if or_key:
            endpoints.append(
                {
                    "name": "openrouter-hermes",
                    "api_key": or_key,
                    "base_url": str(
                        cfg.get("openrouter_base_url") or OPENROUTER_DEFAULT_BASE
                    ).rstrip("/"),
                    "model": hermes["model"],
                    "kind": "openrouter",
                }
            )

    local_base = str(
        cfg.get("local_failover_base_url")
        or cfg.get("ollama_base_url")
        or LOCAL_FALLBACK_BASE
    ).rstrip("/")
    local_model = str(
        cfg.get("local_failover_model") or cfg.get("ollama_fallback_model") or LOCAL_FALLBACK_MODEL
    )
    endpoints.append(
        {
            "name": "local-deepseek-moe",
            "api_key": str(cfg.get("local_failover_api_key") or "sk-no-key-required"),
            "base_url": local_base,
            "model": local_model,
            "kind": "local",
        }
    )
    return endpoints


def _is_retryable(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status in (401, 403, 404, 408, 429, 500, 502, 503, 504):
        return True
    msg = str(exc).lower()
    return any(
        t in msg
        for t in (
            "429",
            "rate",
            "timeout",
            "timed out",
            "connection",
            "503",
            "502",
            "overloaded",
            "quota",
            "unauthorized",
            "forbidden",
            "not found",
            "does not exist",
            "model_not_found",
            "unknown model",
        )
    )


class QuadKeyLoadBalancer:
    """
    Round-robin + failover across NVIDIA keys, then local cluster.

    Use `.chat.completions.create(...)` like a normal OpenAI client; the model
    argument is overridden to the active endpoint's model unless force_model=True.
    """

    def __init__(
        self,
        endpoints: Optional[Sequence[Dict[str, str]]] = None,
        *,
        cfg: Optional[Dict[str, Any]] = None,
        on_failover: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._lock = threading.Lock()
        self._idx = 0
        self._cfg = cfg or {}
        self._on_failover = on_failover
        self.endpoints: List[Dict[str, str]] = list(endpoints or build_endpoints(cfg))
        if not self.endpoints:
            raise RuntimeError("No LLM endpoints configured (NVIDIA keys + local failover).")
        self._clients: List[OpenAI] = []
        for ep in self.endpoints:
            headers = None
            if ep.get("kind") == "openrouter":
                headers = {
                    "HTTP-Referer": str(
                        self._cfg.get("openrouter_http_referer")
                        or self._cfg.get("brain_dashboard_url")
                        or "http://localhost:8888"
                    ),
                    "X-Title": str(self._cfg.get("openrouter_app_title") or "GLaDOS"),
                }
            self._clients.append(
                OpenAI(
                    api_key=ep["api_key"],
                    base_url=ep["base_url"],
                    timeout=httpx.Timeout(LLM_CALL_HARD_TIMEOUT_SEC, connect=8.0),
                    default_headers=headers,
                )
            )
        self.chat = _ChatNamespace(self)
        self.embeddings = _EmbeddingsNamespace(self)
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nim-lb")

    @property
    def active_endpoint(self) -> Dict[str, str]:
        with self._lock:
            return dict(self.endpoints[self._idx % len(self.endpoints)])

    def sync_openai_env(self) -> Dict[str, str]:
        """Point litellm / Open Interpreter at the current primary endpoint."""
        ep = self.endpoints[0]
        # Chat personality stays on NVIDIA when Hermes is only available via OpenRouter.
        for candidate in self.endpoints:
            if candidate.get("kind") == "nvidia":
                ep = candidate
                break
        os.environ["OPENAI_API_KEY"] = ep["api_key"]
        os.environ["OPENAI_API_BASE"] = ep["base_url"]
        os.environ["OPENAI_BASE_URL"] = ep["base_url"]
        os.environ["OPENAI_MODEL_NAME"] = ep["model"]
        return dict(ep)

    def sync_interpreter_env(self) -> Dict[str, str]:
        """Point Open Interpreter at Hermes (tool-calling), falling back to NVIDIA."""
        ep = self.endpoints[0]
        for candidate in self.endpoints:
            model = str(candidate.get("model") or "")
            if candidate.get("kind") == "openrouter" or "hermes" in model.lower():
                ep = candidate
                break
            if candidate.get("kind") == "nvidia" and ep.get("kind") != "nvidia":
                ep = candidate
        os.environ["OPENAI_API_KEY"] = ep["api_key"]
        os.environ["OPENAI_API_BASE"] = ep["base_url"]
        os.environ["OPENAI_BASE_URL"] = ep["base_url"]
        os.environ["OPENAI_MODEL_NAME"] = ep["model"]
        return dict(ep)

    def create(self, *args: Any, force_model: bool = False, **kwargs: Any) -> Any:
        last_err: Optional[BaseException] = None
        n = len(self.endpoints)
        with self._lock:
            start = self._idx % n

        hard_timeout = float(
            self._cfg.get("llm_hard_timeout_sec") or LLM_CALL_HARD_TIMEOUT_SEC
        )

        for offset in range(n):
            i = (start + offset) % n
            ep = self.endpoints[i]
            client = self._clients[i]
            call_kwargs = dict(kwargs)
            if not force_model or not call_kwargs.get("model"):
                call_kwargs["model"] = ep["model"]
            # Skip known-dead local failover quickly when host is down
            if ep.get("kind") == "local":
                hard_timeout = min(hard_timeout, 12.0)
            try:
                fut = self._pool.submit(
                    client.chat.completions.create, *args, **call_kwargs
                )
                try:
                    result = fut.result(timeout=hard_timeout)
                except FuturesTimeout as exc:
                    fut.cancel()
                    raise TimeoutError(
                        f"{ep['name']} hard-timeout after {hard_timeout:.0f}s"
                    ) from exc
                with self._lock:
                    self._idx = i
                return result
            except Exception as exc:
                last_err = exc
                if not _is_retryable(exc) and offset == 0 and ep.get("kind") == "nvidia":
                    # Non-retryable on first key — still try other keys / local
                    pass
                next_ep = self.endpoints[(i + 1) % n]
                msg = (
                    f"[LB] Endpoint {ep['name']} failed ({exc}); "
                    f"failing over → {next_ep['name']}"
                )
                print(msg)
                if self._on_failover:
                    try:
                        self._on_failover(ep["name"], next_ep["name"])
                    except Exception:
                        pass
                time.sleep(0.2 * (offset + 1))
                continue

        raise Exception(
            f"All {n} LLM endpoints exhausted. Last error: {last_err}"
        ) from last_err


class _CompletionsProxy:
    def __init__(self, lb: QuadKeyLoadBalancer) -> None:
        self._lb = lb

    def create(self, *args: Any, **kwargs: Any) -> Any:
        return self._lb.create(*args, **kwargs)


class _ChatNamespace:
    def __init__(self, lb: QuadKeyLoadBalancer) -> None:
        self.completions = _CompletionsProxy(lb)


class _EmbeddingsNamespace:
    def __init__(self, lb: QuadKeyLoadBalancer) -> None:
        self._lb = lb

    def create(self, *args: Any, **kwargs: Any) -> Any:
        last_err: Optional[BaseException] = None
        n = len(self._lb.endpoints)
        with self._lb._lock:
            start = self._lb._idx % n
        for offset in range(n):
            i = (start + offset) % n
            ep = self._lb.endpoints[i]
            if ep.get("kind") != "nvidia":
                # Local deepseek-moe may not expose /embeddings — skip
                continue
            try:
                return self._lb._clients[i].embeddings.create(*args, **kwargs)
            except Exception as exc:
                last_err = exc
                continue
        if last_err:
            raise last_err
        raise RuntimeError("No NVIDIA endpoint available for embeddings.")


def create_nvidia_balanced_client(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    on_failover: Optional[Callable[[str, str], None]] = None,
) -> QuadKeyLoadBalancer:
    return QuadKeyLoadBalancer(cfg=cfg, on_failover=on_failover)
