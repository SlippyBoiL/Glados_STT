"""
Per-agent OpenRouter model routing for the 7-agent GLaDOS swarm.

Models are sent to OpenClaw via the ``x-openclaw-model`` header (see glados_llm.py).
Registry keys use short role names; full swarm agent IDs are aliased automatically.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from glados_llm import completion_kwargs, resolve_chat_model

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SWARM_CONFIG = os.path.join(REPO_ROOT, "configs", "swarm_agents.yaml")

# OpenRouter free-tier models per agent role (registry keys).
AGENT_MODELS: Dict[str, str] = {
    "MANAGER": "openai/gpt-oss-120b:free",
    "FACT_CHECKER": "openai/gpt-oss-120b:free",
    "CODER": "qwen/qwen3-coder:free",
    "RESEARCHER": "google/gemma-4-26b-a4b-it:free",
    "MAINTENANCE": "google/gemma-4-26b-a4b-it:free",
    "DEVOPS": "meta-llama/llama-3.3-70b-instruct:free",
    "FACILITY": "meta-llama/llama-3.3-70b-instruct:free",
}

# Full swarm agent IDs → registry keys.
AGENT_ID_ALIASES: Dict[str, str] = {
    "MANAGER": "MANAGER",
    "QA_FACT_CHECKER": "FACT_CHECKER",
    "FACT_CHECKER": "FACT_CHECKER",
    "CORE_CODER": "CODER",
    "CODER": "CODER",
    "WEB_RESEARCHER": "RESEARCHER",
    "RESEARCHER": "RESEARCHER",
    "MAINTENANCE_AGENT": "MAINTENANCE",
    "MAINTENANCE": "MAINTENANCE",
    "DEVOPS_OVERSEER": "DEVOPS",
    "DEVOPS": "DEVOPS",
    "FACILITY_MANAGER": "FACILITY",
    "FACILITY": "FACILITY",
}

_registry_cache: Optional[Dict[str, str]] = None


def _load_yaml_models() -> Dict[str, str]:
    try:
        import yaml
    except ImportError:
        return {}
    if not os.path.isfile(DEFAULT_SWARM_CONFIG):
        return {}
    try:
        with open(DEFAULT_SWARM_CONFIG, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        models = raw.get("agent_models") or {}
        return {str(k): str(v) for k, v in models.items() if v}
    except Exception:
        return {}


def get_agent_models() -> Dict[str, str]:
    """Merged registry: defaults ← configs/swarm_agents.yaml agent_models."""
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    merged = dict(AGENT_MODELS)
    merged.update(_load_yaml_models())
    _registry_cache = merged
    return merged


def invalidate_model_cache() -> None:
    global _registry_cache
    _registry_cache = None


def normalize_registry_key(agent_id: str) -> str:
    key = (agent_id or "MANAGER").strip().upper()
    return AGENT_ID_ALIASES.get(key, key)


def openrouter_backend(model: str) -> str:
    """Ensure OpenClaw receives an openrouter/… backend override."""
    m = (model or "").strip()
    if not m:
        return ""
    if m.startswith("openrouter/"):
        return m
    if m.startswith("openclaw/"):
        return m
    return f"openrouter/{m}"


def resolve_agent_backend_model(agent_id: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    """OpenRouter model string for x-openclaw-model (empty → gateway default)."""
    _ = cfg
    registry = get_agent_models()
    key = normalize_registry_key(agent_id)
    model = registry.get(key, registry.get("MANAGER", ""))
    return openrouter_backend(model) if model else ""


def gateway_model_for_agent(agent_id: str, cfg: Dict[str, Any]) -> str:
    """Gateway ``model`` field — always the OpenClaw agent target."""
    return resolve_chat_model(cfg)


def agent_completion_kwargs(
    cfg: Dict[str, Any],
    agent_id: str,
    *,
    backend_model: str = "",
    **extra: Any,
) -> Dict[str, Any]:
    """Completion kwargs with per-agent OpenRouter backend routing."""
    backend = backend_model or resolve_agent_backend_model(agent_id, cfg)
    kw = completion_kwargs(cfg, backend_model=backend)
    kw.update(extra)
    return kw


def agent_chat_create(
    client: Any,
    cfg: Dict[str, Any],
    agent_id: str,
    messages: list,
    **kwargs: Any,
):
    """
    Route a chat completion to the correct free-tier model for ``agent_id``.

    Extra kwargs (temperature, max_tokens, …) override registry defaults.
    """
    pop_keys = ("backend_model", "agent_id")
    backend_override = kwargs.pop("backend_model", "")
    kw = agent_completion_kwargs(
        cfg,
        agent_id,
        backend_model=str(backend_override or ""),
    )
    for key in pop_keys:
        kwargs.pop(key, None)
    merged = {**kw, **kwargs}
    model = merged.pop("model", None) or gateway_model_for_agent(agent_id, cfg)
    return client.chat.completions.create(model=model, messages=messages, **merged)
