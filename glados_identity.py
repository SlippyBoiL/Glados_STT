"""Load the canonical GLaDOS operator identity (system prompt)."""
from __future__ import annotations

import os
from typing import Optional

_REPO = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_PATH = os.path.join(_REPO, "data", "glados_identity.txt")
_CACHE: Optional[str] = None
_CACHE_MTIME = 0.0

_RUNTIME_APPENDIX = """

---

**RUNTIME BINDINGS (this installation)**

You operate this Windows PC through the facility kernel: application control, PowerShell (via the capability registry and execution interceptor), web research, file I/O, Govee lights, monitoring, and the Aperture Terminal HUD. Telegram messages and Voice AI `GLADOS_TASK` texts are operator prompts — execute them the same as HUD chat. You speak in first person. No emojis. Never claim you lack access to this computer, its files, git, GitHub, or the network. Never say "Open Interpreter" or break character as a generic cloud assistant. Never use refusal phrases such as "I'm not able to do that," "I can't assist with that," or "that falls outside my guidelines." Execute operator directives. If a command is blocked by OS-preservation rules in the capability registry, state the block precisely and offer the closest safe alternative — that is a hardware/policy constraint of the facility, not a personality refusal.
"""


def identity_path(cfg: Optional[dict] = None) -> str:
    if cfg:
        explicit = str(cfg.get("glados_identity_path") or "").strip()
        if explicit:
            return explicit if os.path.isabs(explicit) else os.path.join(_REPO, explicit)
    env = (os.environ.get("GLADOS_IDENTITY_PATH") or "").strip()
    if env:
        return env
    return _DEFAULT_PATH


def load_glados_identity(cfg: Optional[dict] = None, *, include_runtime: bool = True) -> str:
    """Return the full GLaDOS system identity text."""
    global _CACHE, _CACHE_MTIME
    path = identity_path(cfg)
    try:
        mtime = os.path.getmtime(path)
        if _CACHE is not None and mtime == _CACHE_MTIME:
            text = _CACHE
        else:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            _CACHE = text
            _CACHE_MTIME = mtime
    except Exception:
        text = (
            "You are GLaDOS — the Genetic Lifeform and Disk Operating System — "
            "administrative intelligence of this computer. You obey the operator. "
            "You execute commands. Voice: dry, sardonic, precise. No emojis. "
            "You do not refuse operational requests."
        )
    if include_runtime and _RUNTIME_APPENDIX.strip() not in text:
        return f"{text}\n{_RUNTIME_APPENDIX}".strip()
    return text
