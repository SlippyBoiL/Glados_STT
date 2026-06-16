"""Live action status — terminal, HUD telemetry, and on-disk feed for the dashboard."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional

from glados_paths import resolve_plugins_dir


def make_action_publisher(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    think_fn: Optional[Callable[..., None]] = None,
    hud_log_fn: Optional[Callable[[str], None]] = None,
    telemetry_path: str = "",
) -> Callable[[str], None]:
    plugins = resolve_plugins_dir(cfg)
    live_path = os.path.join(plugins, "live_action.txt")

    def publish(message: str) -> None:
        msg = (message or "").strip()
        if not msg:
            return
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        print(f"[ACTION] {line}")
        try:
            with open(live_path, "w", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        if think_fn:
            try:
                think_fn("organize", msg)
            except Exception:
                pass
        if hud_log_fn:
            try:
                hud_log_fn(f"⚙ {msg}")
            except Exception:
                pass
        if telemetry_path:
            try:
                from plugins.telemetry import telemetry_log  # type: ignore

                telemetry_log(
                    telemetry_path,
                    "action_progress",
                    {"message": msg, "phase": "organize"},
                )
            except Exception:
                try:
                    from telemetry import telemetry_log  # type: ignore

                    telemetry_log(
                        telemetry_path,
                        "action_progress",
                        {"message": msg, "phase": "organize"},
                    )
                except Exception:
                    pass

    return publish
