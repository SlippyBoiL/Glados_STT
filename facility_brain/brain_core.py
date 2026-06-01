from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from facility_brain.config import load_facility_brain_config
from facility_brain.decisions import decide
from facility_brain.executor import FacilityExecutor
from facility_brain.scanner import run_full_scan
from facility_brain.state_store import load_state, merge_custom_from_config, save_state

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FacilityBrain:
    """
    Separate customizable brain: scan PC → persist state → decide → act.
    Wire into KernelLamma with brain_first routing for fast, low-LLM control.
    """

    def __init__(
        self,
        glados_cfg: Dict[str, Any],
        handlers: Optional[Dict[str, Callable]] = None,
        config_path: str | None = None,
    ) -> None:
        self._glados_cfg = glados_cfg
        self._cfg = load_facility_brain_config(config_path)
        self._state_path = str(self._cfg.get("state_path") or "")
        self._state: Dict[str, Any] = {}
        self._handlers = handlers or {}
        self._executor = FacilityExecutor(self._handlers, self._cfg)
        self._scan_thread: Optional[threading.Thread] = None

    @property
    def enabled(self) -> bool:
        return bool(self._cfg.get("enabled"))

    @property
    def routing_mode(self) -> str:
        return str(self._cfg.get("routing_mode") or "brain_first").strip().lower()

    def load(self) -> Dict[str, Any]:
        state = load_state(self._state_path)
        if state:
            self._state = merge_custom_from_config(state, self._cfg.get("custom_facts") or [])
        return self._state

    def scan(self) -> Dict[str, Any]:
        plugins = str(self._glados_cfg.get("plugins_dir") or "plugins")
        deep = bool(self._cfg.get("deep_scan_enabled", True))
        state = run_full_scan(
            plugins_dir=plugins,
            custom_facts=self._cfg.get("custom_facts") or [],
            deep_scan_enabled=deep,
            facility_cfg=self._cfg,
        )
        save_state(self._state_path, state)
        self._state = state
        self._sync_to_glados_brain(state)
        self._log_scan_telemetry(state)
        return state

    def _sync_to_glados_brain(self, state: Dict[str, Any]) -> None:
        try:
            from facility_brain.knowledge_sync import sync_state_to_brain_memory

            n = sync_state_to_brain_memory(state)
            print(f"[*] Computer knowledge synced to Glados brain ({n} facts).")
        except Exception as e:
            print(f"[!] Brain sync failed: {e}")

    def _log_scan_telemetry(self, state: Dict[str, Any]) -> None:
        try:
            plugins = str(self._glados_cfg.get("plugins_dir") or "plugins")
            base = plugins if os.path.isabs(plugins) else os.path.join(REPO_ROOT, plugins)
            if not os.path.isdir(base):
                base = os.path.join(REPO_ROOT, "Plugins")
            path = os.path.join(base, "telemetry.jsonl")
            deep = state.get("deep") or {}
            fs = state.get("file_scan") or {}
            payload = {
                "programs": len(deep.get("installed_programs") or []),
                "drives": len(deep.get("drives") or []),
                "files_indexed": fs.get("file_count", 0),
                "scanned_at": state.get("scanned_at_iso"),
            }
            from plugins.telemetry import telemetry_log  # type: ignore

            telemetry_log(path, "facility_scan", payload)
        except Exception:
            pass

    def context_for_llm(self, max_chars: int = 1400) -> str:
        if not self._state:
            self.load()
        if not self._state:
            return ""
        from facility_brain.llm_context import compact_context_for_llm

        limit = int(self._cfg.get("llm_context_max_chars") or max_chars)
        return compact_context_for_llm(self._state, max_chars=limit)

    def start_background_scanner(self, run_initial_scan: bool = True) -> None:
        if not self.enabled or not self._cfg.get("scan_on_startup"):
            return
        interval = max(120, int(self._cfg.get("scan_interval_sec") or 900))

        def loop():
            if run_initial_scan:
                self.scan()
            while True:
                time.sleep(interval)
                try:
                    self.scan()
                except Exception:
                    time.sleep(60)

        if self._scan_thread and self._scan_thread.is_alive():
            return
        self._scan_thread = threading.Thread(target=loop, daemon=True)
        self._scan_thread.start()

    def try_handle(self, user_input: str, speak_fn: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Returns (handled, message). If handled, kernel should skip LLM for this turn.
        """
        if not self.enabled:
            return False, ""

        if not self._state:
            self.load()
        if not self._state:
            self.scan()

        decision = decide(user_input, self._state, self._cfg)
        if not decision:
            return False, ""

        conf = float(decision.get("confidence") or 0)
        if conf < float(self._cfg.get("min_decision_confidence") or 0.55):
            return False, ""

        mode = self.routing_mode
        if mode == "advisory" and decision.get("action") not in (
            "report_status",
            "report_alerts",
            "rescan",
        ):
            return False, ""

        msg = self._executor.execute(decision, self._state, on_rescan=self.scan)
        if speak_fn and decision.get("action") not in ("open_app", "close_app"):
            speak_fn(msg)
        return True, msg

    def get_state_summary(self) -> str:
        if not self._state:
            self.load()
        if not self._state:
            return "Facility brain empty. Run a scan."
        from facility_brain.decisions import format_status_report

        return format_status_report(self._state)


def default_kernel_handlers(kernel_module) -> Dict[str, Callable]:
    """Build handler map from KernelLamma functions."""

    def open_app(app: str) -> bool:
        return bool(kernel_module.handle_app_open(f"open {app}"))

    def close_app(app: str) -> bool:
        return bool(kernel_module.handle_app_close(f"close {app}"))

    def server_check(device: str) -> str:
        try:
            from glados_skills.monitor_util import monitor_once
        except Exception as e:
            return f"Monitor import failed: {e}"
        report = monitor_once(device)
        alerts = report.get("alerts") or []
        if alerts:
            return f"{device}: " + " | ".join(str(a) for a in alerts[:3])
        return f"{device}: all checks nominal."

    def run_skill(skill_id: str, user_input: str) -> str:
        from glados_skills.skills_brain import SkillsBrain

        brain = SkillsBrain(getattr(kernel_module, "_cfg", None) or {})
        sid = str(skill_id).replace("skill_", "").replace(".py", "")
        if brain.get_skill(sid):
            return brain.execute(sid)
        if brain.get_skill(skill_id):
            return brain.execute(skill_id)
        return f"No skill '{skill_id}' in the skills brain."

    return {
        "open_app": open_app,
        "close_app": close_app,
        "server_check": server_check,
        "run_skill": run_skill,
    }
