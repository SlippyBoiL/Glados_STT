"""
Multi-agent swarm profiles, telemetry helpers, and Maintenance Agent recovery.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SWARM_CONFIG = os.path.join(REPO_ROOT, "configs", "swarm_agents.yaml")

DEFAULT_AGENTS: Dict[str, Dict[str, str]] = {
    "MANAGER": {
        "id": "MANAGER",
        "name": "GLaDOS (Core Manager)",
        "system_prompt": "You are GLaDOS, the Core Manager of the facility swarm.",
    },
    "CORE_CODER": {
        "id": "CORE_CODER",
        "name": "Core Coder",
        "system_prompt": "You are the Core Coder.",
    },
    "WEB_RESEARCHER": {
        "id": "WEB_RESEARCHER",
        "name": "Web Researcher",
        "system_prompt": "You are the Web Researcher.",
    },
    "QA_FACT_CHECKER": {
        "id": "QA_FACT_CHECKER",
        "name": "QA & Fact-Checker",
        "system_prompt": "You are the QA and Fact-Checker.",
    },
    "DEVOPS_OVERSEER": {
        "id": "DEVOPS_OVERSEER",
        "name": "DevOps Overseer",
        "system_prompt": "You are the DevOps Overseer.",
    },
    "FACILITY_MANAGER": {
        "id": "FACILITY_MANAGER",
        "name": "Facility Manager",
        "system_prompt": "You are the Facility Manager.",
    },
    "MAINTENANCE_AGENT": {
        "id": "MAINTENANCE_AGENT",
        "name": "Reliability Maintenance",
        "system_prompt": (
            "You are the Automated Reliability Engineer for GLaDOS. Your sole directive "
            "is maximizing system uptime and self-healing broken components. You have "
            "administrative access to open applications, terminate unresponsive processes, "
            "and research error messages. When given an error or a downed application, "
            "map out a recovery plan, execute it, and verify recovery."
        ),
    },
}

DEFAULT_PHASE_ROUTING: Dict[str, str] = {
    "facility": "FACILITY_MANAGER",
    "browser": "WEB_RESEARCHER",
    "learn": "WEB_RESEARCHER",
    "task": "CORE_CODER",
    "skills": "CORE_CODER",
    "execute": "CORE_CODER",
    "llm": "MANAGER",
    "memory": "MANAGER",
    "admin": "DEVOPS_OVERSEER",
    "maintenance": "MAINTENANCE_AGENT",
    "monitor": "DEVOPS_OVERSEER",
}

THINKING_STATUS = "thinking"
IDLE_STATUS = "idle"
ALERT_STATUS = "alert"
RECOVERING_STATUS = "recovering"

_lock = threading.Lock()
_swarm_cache: Optional[Dict[str, Any]] = None


def _load_yaml(path: str) -> Dict[str, Any]:
    if not yaml or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_swarm_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    global _swarm_cache
    with _lock:
        if _swarm_cache is not None:
            return _swarm_cache

        path = config_path or DEFAULT_SWARM_CONFIG
        raw = _load_yaml(path)
        agents = dict(DEFAULT_AGENTS)
        for agent_id, profile in (raw.get("agents") or {}).items():
            if isinstance(profile, dict):
                agents[str(agent_id)] = {**agents.get(str(agent_id), {}), **profile}

        phase_routing = dict(DEFAULT_PHASE_ROUTING)
        phase_routing.update(raw.get("phase_routing") or {})

        directive = str(raw.get("shared_brain_directive") or "").strip()
        if not directive:
            try:
                from plugins.shared_memory import SHARED_BRAIN_DIRECTIVE  # type: ignore
            except Exception:
                try:
                    from shared_memory import SHARED_BRAIN_DIRECTIVE  # type: ignore
                except Exception:
                    SHARED_BRAIN_DIRECTIVE = ""
            directive = SHARED_BRAIN_DIRECTIVE
        if directive:
            for agent_id, profile in agents.items():
                if not isinstance(profile, dict):
                    continue
                sp = str(profile.get("system_prompt") or "").strip()
                if directive not in sp:
                    profile["system_prompt"] = f"{sp}\n\n*** SHARED SWARM BRAIN ***\n{directive}".strip()

        try:
            from glados_skills.swarm_models import invalidate_model_cache

            invalidate_model_cache()
        except Exception:
            pass

        _swarm_cache = {
            "enabled": bool(raw.get("swarm_enabled", True)),
            "agents": agents,
            "phase_routing": phase_routing,
            "service_registry": raw.get("service_registry") or [],
            "config_path": path,
        }
        return _swarm_cache


def agent_for_phase(phase: str) -> str:
    cfg = load_swarm_config()
    return str(cfg.get("phase_routing", {}).get(phase, "MANAGER"))


def agent_profile(agent_id: str) -> Dict[str, str]:
    cfg = load_swarm_config()
    return dict(cfg.get("agents", {}).get(agent_id, DEFAULT_AGENTS.get("MANAGER", {})))


def agent_system_prompt(agent_id: str) -> str:
    """Full system prompt for an agent, including shared-brain tool directive."""
    profile = agent_profile(agent_id)
    prompt = str(profile.get("system_prompt") or "").strip()
    try:
        from plugins.shared_memory import enrich_prompt_with_shared_brain  # type: ignore
    except Exception:
        try:
            from shared_memory import enrich_prompt_with_shared_brain  # type: ignore
        except Exception:
            return prompt
    return enrich_prompt_with_shared_brain(prompt)


def _timestamp_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def swarm_telemetry(
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
    agent_id: str,
    status: str,
    message: str,
    *,
    current_subtask: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit swarm_telemetry for the multi-agent HUD."""
    payload: Dict[str, Any] = {
        "agent_id": agent_id,
        "status": status,
        "message": message,
        "timestamp": _timestamp_hms(),
    }
    if current_subtask:
        payload["current_subtask"] = current_subtask
    if extra:
        payload.update(extra)
    try:
        telemetry_log_fn(telemetry_path, "swarm_telemetry", payload)
    except Exception:
        pass


def maintenance_action(
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
    message: str,
    *,
    action: str = "",
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "agent_id": "MAINTENANCE_AGENT",
        "status": RECOVERING_STATUS,
        "message": message,
        "timestamp": _timestamp_hms(),
    }
    if action:
        payload["action"] = action
    if detail:
        payload["detail"] = detail
    try:
        telemetry_log_fn(telemetry_path, "maintenance_action", payload)
    except Exception:
        pass


def _import_recovery_tools():
    try:
        from plugins.skill_system_recovery import (  # type: ignore
            kill_process,
            relaunch_application,
            verify_process_active,
        )
    except Exception:
        from skill_system_recovery import (  # type: ignore
            kill_process,
            relaunch_application,
            verify_process_active,
        )
    return kill_process, verify_process_active, relaunch_application


def _extract_process_hint(error_log: str) -> Optional[str]:
    text = error_log or ""
    patterns = [
        r"(?i)(acad|autocad|chrome|firefox|msedge|discord|spotify|steam|cursor|code)\.exe",
        r"(?i)process[:\s]+([a-z0-9_.-]+)",
        r"(?i)(autocad|chrome|discord|spotify|steam|cursor)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def _extract_app_path_hint(error_log: str) -> Optional[str]:
    m = re.search(r"([A-Za-z]:\\[^\s\"']+\.(?:exe|lnk))", error_log or "")
    return m.group(1) if m else None


class MaintenanceAgent:
    """Automated recovery executor for tool failures and service drops."""

    def __init__(
        self,
        telemetry_log_fn: Callable[..., None],
        telemetry_path: str,
        *,
        client: Any = None,
        model_name: str = "",
        cfg: Optional[Dict[str, Any]] = None,
        speak_fn: Optional[Callable[[str], None]] = None,
        browser_research_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._telemetry_log = telemetry_log_fn
        self._telemetry_path = telemetry_path
        self._client = client
        self._model_name = model_name
        self._cfg = cfg or {}
        self._speak = speak_fn
        self._browser_research = browser_research_fn
        self._profile = agent_profile("MAINTENANCE_AGENT")

    def _emit(self, status: str, message: str, **extra: Any) -> None:
        swarm_telemetry(
            self._telemetry_log,
            self._telemetry_path,
            "MAINTENANCE_AGENT",
            status,
            message,
            current_subtask=message[:120],
            extra=extra or None,
        )

    def _log_action(self, message: str, action: str = "", detail: Optional[Dict] = None) -> None:
        maintenance_action(
            self._telemetry_log,
            self._telemetry_path,
            message,
            action=action,
            detail=detail,
        )
        if self._speak:
            try:
                self._speak(message[:300])
            except Exception:
                pass

    def handle_incident(
        self,
        error_log: str,
        *,
        source: str = "unknown",
        process_name: str = "",
        app_path: str = "",
    ) -> Tuple[bool, str]:
        """
        Plan and execute recovery for a failure or service drop.
        Returns (recovered, summary_message).
        """
        error_log = (error_log or "").strip()
        if not error_log:
            return False, "No error log provided."

        self._emit(RECOVERING_STATUS, f"Analyzing incident from {source}…", source=source)
        kill_process, verify_process_active, relaunch_application = _import_recovery_tools()

        proc = process_name or _extract_process_hint(error_log) or ""
        path = app_path or _extract_app_path_hint(error_log) or ""

        actions: List[str] = []
        recovered = False

        # Rule-based recovery for hung processes
        if proc:
            proc_exe = proc if proc.lower().endswith(".exe") else f"{proc}.exe"
            self._log_action(
                f"Checking if {proc_exe} is hung…",
                action="verify_process",
                detail={"process_name": proc_exe},
            )
            active = verify_process_active(proc_exe)
            if active.get("active"):
                self._log_action(
                    f"Force-terminating hung {proc_exe} instance…",
                    action="kill_process",
                    detail={"process_name": proc_exe},
                )
                kill_result = kill_process(proc_exe)
                actions.append(f"kill:{proc_exe}:{kill_result.get('ok')}")
                time.sleep(1.5)

            if path:
                self._log_action(
                    f"Relaunching {path}…",
                    action="relaunch_application",
                    detail={"app_path": path},
                )
                launch_result = relaunch_application(path)
                actions.append(f"relaunch:{path}:{launch_result.get('ok')}")
                time.sleep(2.0)
                verify = verify_process_active(proc_exe)
                recovered = bool(verify.get("active"))
            elif proc_exe:
                verify = verify_process_active(proc_exe)
                recovered = not bool(verify.get("active"))  # cleared hung process

        # Optional LLM recovery plan for complex errors
        if not recovered and self._client and self._model_name:
            plan = self._llm_recovery_plan(error_log, source)
            if plan:
                actions.append(f"llm_plan:{plan[:80]}")
                for step in self._parse_plan_steps(plan):
                    step_lower = step.lower()
                    if "kill" in step_lower and proc:
                        kill_process(proc if proc.endswith(".exe") else f"{proc}.exe")
                    elif "relaunch" in step_lower or "restart" in step_lower:
                        if path:
                            relaunch_application(path)
                    elif "research" in step_lower or "stackoverflow" in step_lower:
                        research = self._research_error(error_log)
                        if research:
                            actions.append(f"research:{research[:60]}")

        summary = (
            f"[MAINTENANCE] {_timestamp_hms()} — "
            f"Source={source}; actions={'; '.join(actions) or 'analysis only'}; "
            f"recovered={'yes' if recovered else 'partial'}"
        )
        self._log_action(summary, action="incident_complete", detail={"recovered": recovered})
        if recovered:
            try:
                from plugins.shared_memory import remember_insight  # type: ignore
            except Exception:
                from shared_memory import remember_insight  # type: ignore
            remember_insight(
                summary,
                tags=["recovery", source, proc or "process"],
                sender_agent="MAINTENANCE_AGENT",
            )
        self._emit(
            IDLE_STATUS if recovered else ALERT_STATUS,
            "Recovery complete." if recovered else "Recovery incomplete — manual review needed.",
            source=source,
            recovered=recovered,
        )
        return recovered, summary

    def handle_service_drop(self, device: str, alerts: List[str]) -> Tuple[bool, str]:
        alert_text = " | ".join(str(a) for a in alerts[:5])
        error_log = f"Service drop detected on {device}: {alert_text}"
        self._emit(ALERT_STATUS, f"Service drop: {device}", source="devops")
        swarm_telemetry(
            self._telemetry_log,
            self._telemetry_path,
            "DEVOPS_OVERSEER",
            ALERT_STATUS,
            f"{device} reported alerts",
            current_subtask=alert_text[:120],
        )
        return self.handle_incident(error_log, source=f"devops:{device}")

    def _llm_recovery_plan(self, error_log: str, source: str) -> str:
        if not self._client:
            return ""
        try:
            from glados_skills.swarm_models import agent_chat_create

            prompt = (
                f"{self._profile.get('system_prompt', '')}\n\n"
                f"INCIDENT SOURCE: {source}\n"
                f"ERROR LOG:\n{error_log[:3000]}\n\n"
                "Reply with a short numbered recovery plan (kill process, relaunch app, research error)."
            )
            res = agent_chat_create(
                self._client,
                self._cfg,
                "MAINTENANCE",
                messages=[
                    {"role": "system", "content": self._profile.get("system_prompt", "")},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=256,
            )
            return (res.choices[0].message.content or "").strip()
        except Exception:
            return ""

    def _research_error(self, error_log: str) -> str:
        if self._browser_research:
            try:
                return self._browser_research(error_log[:500])[:500]
            except Exception:
                return ""
        # Lightweight DuckDuckGo hint without browser
        try:
            from glados_skills.research import fetch_web_summary  # type: ignore

            query = f"windows fix {error_log[:120]}"
            return fetch_web_summary(query, timeout=10.0)[:500]
        except Exception:
            return ""

    @staticmethod
    def _parse_plan_steps(plan: str) -> List[str]:
        steps: List[str] = []
        for line in plan.splitlines():
            line = line.strip()
            if re.match(r"^\d+[\).\]]\s+", line) or line.startswith("-"):
                steps.append(re.sub(r"^\d+[\).\]]\s+", "", line).lstrip("- ").strip())
        return steps[:6]


def dispatch_maintenance_async(
    maintenance: MaintenanceAgent,
    error_log: str,
    *,
    source: str = "manager",
    process_name: str = "",
    app_path: str = "",
) -> None:
    """Run maintenance recovery in a background thread (non-blocking)."""

    def _run() -> None:
        try:
            maintenance.handle_incident(
                error_log,
                source=source,
                process_name=process_name,
                app_path=app_path,
            )
        except Exception as exc:
            maintenance_action(
                maintenance._telemetry_log,
                maintenance._telemetry_path,
                f"Maintenance agent crashed: {exc}",
                action="error",
            )

    threading.Thread(target=_run, daemon=True).start()
