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


def swarm_telemetry_log(
    telemetry_path: str,
    agent_id: str,
    status: str,
    message: str,
    **extra: Any,
) -> None:
    """Multi-agent swarm status for the command dashboard."""
    from datetime import datetime

    payload: Dict[str, Any] = {
        "agent_id": agent_id,
        "status": status,
        "message": message,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    if extra:
        payload.update(extra)
    telemetry_log(telemetry_path, "swarm_telemetry", payload)


def system_metrics_log(telemetry_path: str, metrics: Dict[str, Any]) -> None:
    """Push psutil host metrics over the telemetry WebSocket stream."""
    from datetime import datetime

    payload = {
        "metrics": {
            "cpu": metrics.get("cpu_percent", 0),
            "ram": metrics.get("ram_percent", 0),
            "disk": metrics.get("disk_percent", 0),
        },
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "detail": metrics,
    }
    telemetry_log(telemetry_path, "system_metrics", payload)


def brain_update_log(
    telemetry_path: str,
    sender_agent: str,
    insight_preview: str,
    *,
    tags: Optional[list] = None,
    insight_id: str = "",
    ok: bool = True,
) -> None:
    """HUD flash when the central shared brain writes a new insight."""
    from datetime import datetime

    payload: Dict[str, Any] = {
        "action": "remember_insight",
        "ok": ok,
        "sender_agent": sender_agent,
        "insight_preview": (insight_preview or "")[:300],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    if tags:
        payload["tags"] = list(tags)
    if insight_id:
        payload["insight_id"] = insight_id
    telemetry_log(telemetry_path, "brain_update", payload)

