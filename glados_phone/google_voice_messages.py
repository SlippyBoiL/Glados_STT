"""Google Voice SMS polling was removed."""
from __future__ import annotations

from typing import Any, Dict, Optional


def start_google_voice_sms_daemon(_cfg: Optional[Dict[str, Any]] = None) -> bool:
    return False


def stop_google_voice_sms_daemon() -> None:
    return None
