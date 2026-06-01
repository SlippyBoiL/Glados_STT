from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional

_LOCK = threading.Lock()


def telemetry_log(telemetry_path: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """
    Append a single JSON line event to `telemetry_path`.

    This is intentionally lightweight and kernel-safe:
    - never raises outward
    - uses a lock to avoid interleaved writes from threads
    """
    try:
        os.makedirs(os.path.dirname(telemetry_path), exist_ok=True)
        event = {
            "ts": time.time(),
            "event_type": event_type,
            "payload": payload or {},
        }
        line = json.dumps(event, ensure_ascii=False)
        with _LOCK:
            with open(telemetry_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        # Telemetry must not break the kernel.
        pass


def thinking_log(
    telemetry_path: str,
    phase: str,
    message: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Structured thought-step for the brain HUD (event_type: thinking)."""
    payload: Dict[str, Any] = {"phase": phase, "message": message}
    if detail:
        payload.update(detail)
    telemetry_log(telemetry_path, "thinking", payload)

