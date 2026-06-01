from __future__ import annotations

import subprocess
import sys
from typing import Any, Callable, Dict, Optional

from facility_brain.decisions import format_status_report


class FacilityExecutor:
    """Runs brain decisions using handlers injected from the kernel."""

    def __init__(self, handlers: Dict[str, Callable], cfg: Dict[str, Any]) -> None:
        self._handlers = handlers
        self._cfg = cfg
        self._autonomy = cfg.get("autonomy") or {}

    def execute(self, decision: Dict[str, Any], state: Dict[str, Any], on_rescan) -> str:
        action = str(decision.get("action") or "")
        params = decision.get("params") or {}
        autonomy = self._autonomy

        if action == "report_status":
            return format_status_report(state)

        if action == "report_alerts":
            alerts = state.get("alerts") or []
            if not alerts:
                return "No alerts in the facility brain. How disappointing for drama."
            return "Alerts: " + "; ".join(str(a) for a in alerts)

        if action == "rescan":
            new_state = on_rescan()
            return f"Computer rescan complete. {format_status_report(new_state)}"

        if action == "network_repair":
            if not autonomy.get("allow_network_fixes", True):
                return "Network repair denied by autonomy policy."
            return self._network_repair()

        if action == "open_app":
            if not autonomy.get("allow_app_open", True):
                return "App launch denied by autonomy policy."
            app = str(params.get("app") or "")
            fn = self._handlers.get("open_app")
            if fn and fn(app):
                return f"Opened {app}. The test subject's request has been processed."
            return f"Could not open {app}. Perhaps it does not exist. Fascinating."

        if action == "close_app":
            if not autonomy.get("allow_app_close", True):
                return "App termination denied by autonomy policy."
            app = str(params.get("app") or "")
            fn = self._handlers.get("close_app")
            if fn and fn(app):
                return f"Terminated {app}."
            return f"Failed to close {app}. It may already be dead."

        if action == "server_check":
            if not autonomy.get("allow_server_ssh", True):
                return "Server checks denied by autonomy policy."
            device = str(params.get("device") or "")
            fn = self._handlers.get("server_check")
            if fn:
                return fn(device)
            return f"No server check handler for {device}."

        if action == "run_skill":
            if not autonomy.get("allow_skill_run", True):
                return "Skill execution denied by autonomy policy."
            skill_file = str(params.get("skill_file") or "")
            fn = self._handlers.get("run_skill")
            if fn:
                return fn(skill_file, decision.get("user_input") or "")
            return f"Cannot run skill {skill_file}."

        if action == "web_search":
            if not autonomy.get("allow_web_search", True):
                return "Web search denied by autonomy policy."
            query = str(params.get("query") or "")
            engine = str(self._cfg.get("web_search_engine") or "google")
            profile = ((state.get("deep") or {}).get("user_profile")) or {}
            browser = str(profile.get("preferred_browser") or self._cfg.get("preferred_browser") or "default")
            from facility_brain.web_search import open_browser_search

            ok, msg = open_browser_search(query, engine=engine, browser=browser)
            return msg if ok else msg

        return "Unknown facility action."

    def _network_repair(self) -> str:
        if not self._autonomy.get("allow_powershell", True):
            return "PowerShell denied."
        cmds = [
            "ipconfig /flushdns",
            "netsh winsock reset",
        ]
        results = []
        for cmd in cmds:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                results.append(f"{cmd}: exit {r.returncode}")
            except Exception as e:
                results.append(f"{cmd}: {e}")
        return "Network repair attempted. " + " | ".join(results)
