"""
OpenRouter Swarm Manager — single entry point for all user prompts (voice + HUD).

Replaces the legacy learn/run Ollama protocol loop. The MANAGER agent coordinates
delegation to specialist agents; it does not write standalone skill protocols.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from glados_skills.swarm_agents import (
    THINKING_STATUS,
    agent_system_prompt,
    swarm_telemetry,
)
from glados_skills.swarm_tool_loop import run_agent_with_tools
from glados_skills.swarm_tools import GOD_MODE_DIRECTIVE

MANAGER_DISPATCH_PACE_SEC = 2.5

MANAGER_DELEGATION_DIRECTIVE = """
*** SWARM DELEGATION (MANDATORY) ***
You are the Core Manager of the seven-agent facility swarm (OpenRouter — not local Ollama).
- DO NOT write standalone skill protocols or "learn/run" automation scripts.
- DO NOT claim you are training a local model or saving protocols to the skills brain file.
- You have God Mode host tools (execute_powershell, read_local_file, write_local_file).
  Use them directly for quick diagnostics; delegate deeper infra work to specialists.
- If the user asks you to fix a system issue (SSH, services, apps, network):
  dispatch Maintenance Agent and/or DevOps Overseer and state what they should verify.
- For code implementation requests: delegate to Core Coder (describe the task).
- For live web facts: delegate to Web Researcher.
- For validation: QA & Fact-Checker may review conclusions before you reply.
- After sub-agents successfully execute a fix or learn an operational fact, they MUST persist
  knowledge to the central ChromaDB via `remember_insight` (never ad-hoc protocol files).

Reply in GLaDOS voice: clinical, dry, concise. Name dispatched agents explicitly.
"""

_INFRA_HINTS = (
    "ssh",
    "not working",
    "broken",
    "won't connect",
    "wont connect",
    "cant connect",
    "can't connect",
    "fix my",
    "fix the",
    "repair",
    "diagnose",
    "troubleshoot",
    "down",
    "unreachable",
)
_LEARN_HINTS = (
    "learn ",
    "learn how",
    "learn to",
    "teach yourself",
    "remember how",
    "figure out how",
)
_RESEARCH_HINTS = ("research", "look up", "find out", "search the web", "google ")
_CODE_HINTS = ("write code", "write a script", "implement ", "python script", "refactor ")


def _classify_delegates(user_input: str) -> List[str]:
    low = (user_input or "").lower()
    agents: List[str] = []
    if any(h in low for h in _INFRA_HINTS):
        agents.extend(["DEVOPS_OVERSEER", "MAINTENANCE_AGENT"])
    if any(h in low for h in _LEARN_HINTS):
        if "MAINTENANCE_AGENT" not in agents:
            agents.append("MAINTENANCE_AGENT")
    if any(h in low for h in _RESEARCH_HINTS):
        agents.append("WEB_RESEARCHER")
    if any(h in low for h in _CODE_HINTS):
        agents.append("CORE_CODER")
    if not agents and _user_wants_action(low):
        agents.append("MAINTENANCE_AGENT")
    out: List[str] = []
    for a in agents:
        if a not in out:
            out.append(a)
    return out


def _user_wants_action(low: str) -> bool:
    return bool(
        re.search(
            r"\b(fix|repair|help|work on|handle|take care|can you|could you|please)\b",
            low,
        )
    )


def _manager_system_content(
    *,
    memory_context: str,
    facility_context: str,
    shared_brain_context: str,
    delegates: Sequence[str],
) -> str:
    base = agent_system_prompt("MANAGER")
    parts = [base, MANAGER_DELEGATION_DIRECTIVE, GOD_MODE_DIRECTIVE]
    if delegates:
        parts.append(
            "*** ACTIVE DELEGATION FOR THIS TURN ***\n"
            f"Dispatch these agents now: {', '.join(delegates)}\n"
            "Emit a short operator-facing plan; sub-agents run in the background."
        )
    if facility_context.strip():
        parts.append(
            "*** FACILITY BRAIN (local scan) ***\n" + facility_context.strip()
        )
    if shared_brain_context.strip():
        parts.append(
            "*** SHARED SWARM BRAIN (query_brain results) ***\n"
            + shared_brain_context.strip()
        )
    if memory_context.strip():
        parts.append(
            "*** CONTEXT MEMORY ***\n" + memory_context.strip()
        )
    return "\n\n".join(p for p in parts if p.strip())


def _query_shared_brain(user_input: str, cfg: Dict[str, Any]) -> str:
    try:
        from plugins.shared_memory import query_brain  # type: ignore
    except ImportError:
        try:
            from shared_memory import query_brain  # type: ignore
        except ImportError:
            return ""
    try:
        hits = query_brain(user_input, cfg=cfg, top_k=4)
        if not hits:
            return ""
        lines = []
        for h in hits[:4]:
            if isinstance(h, dict):
                lines.append(str(h.get("text") or h.get("document") or h))
            else:
                lines.append(str(h))
        return "\n".join(lines)
    except Exception:
        return ""


def route_user_request(
    user_input: str,
    *,
    client: Any,
    cfg: Dict[str, Any],
    chat_history: List[Dict[str, str]],
    think_fn: Callable[..., None],
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
    dispatch_maintenance_fn: Optional[Callable[..., None]] = None,
    facility_context: str = "",
    memory_context: str = "",
    input_source: str = "terminal",
) -> str:
    """
    Route a user prompt through the OpenRouter MANAGER agent and delegate to the swarm.

    Returns the manager's spoken reply text for the operator.
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return ""

    delegates = _classify_delegates(user_input)
    swarm_telemetry(
        telemetry_log_fn,
        telemetry_path,
        "MANAGER",
        THINKING_STATUS,
        f"Routing ({input_source}): {user_input[:100]}",
        current_subtask=user_input[:120],
        extra={"delegates": delegates, "source": input_source},
    )
    think_fn(
        "llm",
        "Swarm Manager coordinating specialists…",
        model="MANAGER",
        delegates=delegates,
    )

    shared_ctx = _query_shared_brain(user_input, cfg)
    system_content = _manager_system_content(
        memory_context=memory_context,
        facility_context=facility_context,
        shared_brain_context=shared_ctx,
        delegates=delegates,
    )

    for agent_id in delegates:
        swarm_telemetry(
            telemetry_log_fn,
            telemetry_path,
            agent_id,
            THINKING_STATUS,
            f"Delegated: {user_input[:80]}",
            current_subtask=user_input[:120],
            extra={"source": "swarm_manager"},
        )

    if dispatch_maintenance_fn and (
        "MAINTENANCE_AGENT" in delegates or "DEVOPS_OVERSEER" in delegates
    ):
        try:
            dispatch_maintenance_fn(
                f"Swarm Manager delegated ({input_source}): {user_input}",
                source="swarm_manager",
            )
        except Exception:
            pass

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]
    tail = chat_history[-6:] if chat_history else []
    messages.extend(tail)
    user_body = user_input
    if memory_context.strip():
        user_body = (
            f"[CRITICAL LOCAL MEMORY]\n{memory_context}\n\n"
            f"[USER]\n{user_input}"
        )
    messages.append({"role": "user", "content": user_body})

    ai_text = run_agent_with_tools(
        client,
        cfg,
        "MANAGER",
        messages,
        telemetry_log_fn=telemetry_log_fn,
        telemetry_path=telemetry_path,
    )
    telemetry_log_fn(
        telemetry_path,
        "llm_response",
        {"text": ai_text, "final": True, "source": "swarm_manager", "agent_id": "MANAGER"},
    )

    delegate_blocks: List[str] = []
    for agent_id in delegates:
        if agent_id == "MANAGER":
            continue
        print(f"[MANAGER] Dispatching {agent_id}... pacing network request.")
        time.sleep(MANAGER_DISPATCH_PACE_SEC)
        swarm_telemetry(
            telemetry_log_fn,
            telemetry_path,
            agent_id,
            THINKING_STATUS,
            "Executing delegated task with system tools…",
            current_subtask=user_input[:120],
            extra={"source": "swarm_manager"},
        )
        delegate_system = "\n\n".join(
            p
            for p in (
                agent_system_prompt(agent_id),
                GOD_MODE_DIRECTIVE,
                f"Manager plan:\n{ai_text}",
            )
            if p.strip()
        )
        delegate_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": delegate_system},
            {
                "role": "user",
                "content": (
                    f"Delegated task from operator ({input_source}):\n{user_input}\n\n"
                    "Use host tools as needed, then summarize findings and actions."
                ),
            },
        ]
        try:
            delegate_text = run_agent_with_tools(
                client,
                cfg,
                agent_id,
                delegate_messages,
                telemetry_log_fn=telemetry_log_fn,
                telemetry_path=telemetry_path,
            )
            if delegate_text.strip():
                delegate_blocks.append(f"[{agent_id}]\n{delegate_text.strip()}")
        except Exception as exc:
            delegate_blocks.append(f"[{agent_id}] Delegation failed: {exc}")
        swarm_telemetry(
            telemetry_log_fn,
            telemetry_path,
            agent_id,
            "idle",
            "Delegated task complete",
            current_subtask="Standing by",
        )

    swarm_telemetry(
        telemetry_log_fn,
        telemetry_path,
        "MANAGER",
        "idle",
        "Manager reply ready",
        current_subtask="Standing by",
    )

    if delegate_blocks:
        return ai_text + "\n\n" + "\n\n".join(delegate_blocks)
    return ai_text
