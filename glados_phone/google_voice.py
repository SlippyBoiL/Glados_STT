"""Google Voice was removed. These stubs keep old imports from opening Chrome."""
from __future__ import annotations

from typing import Any, Dict, Optional


def operator_number(_cfg: Optional[Dict[str, Any]] = None) -> str:
    return ""


def start_google_voice_line(_cfg: Optional[Dict[str, Any]] = None) -> bool:
    return False


def voice_line_busy() -> bool:
    return False


def place_google_voice_call(
    _cfg: Optional[Dict[str, Any]] = None,
    *,
    to_number: str = "",
    message: str = "",
) -> Dict[str, Any]:
    return {
        "ok": False,
        "provider": "google_voice",
        "detail": "Google Voice integration removed",
        "to": to_number or "",
        "message": message or "",
    }


def open_chrome_url(*_args: Any, **_kwargs: Any) -> bool:
    return False
