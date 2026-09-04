"""
OpenRouter tool-calling loop for swarm agents (God Mode).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from glados_skills.swarm_models import agent_chat_create
from glados_skills.swarm_agents import THINKING_STATUS, swarm_telemetry
from glados_skills.swarm_tools import (
    SWARM_CORE_TOOLS,
    assistant_message_dict,
    execute_swarm_tool,
    parse_tool_arguments,
)

DEFAULT_MAX_TOOL_ROUNDS = 8


def _rate_limit_retry_telemetry(
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
    agent_id: str,
) -> Callable[[int], None]:
    def _on_retry(sleep_time: int) -> None:
        swarm_telemetry(
            telemetry_log_fn,
            telemetry_path,
            agent_id,
            THINKING_STATUS,
            f"Server congested. Retrying request in {sleep_time} seconds...",
        )

    return _on_retry


def _local_fallback_telemetry(
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
    agent_id: str,
) -> Callable[[], None]:
    def _on_fallback() -> None:
        swarm_telemetry(
            telemetry_log_fn,
            telemetry_path,
            agent_id,
            THINKING_STATUS,
            "Cloud API locked. Rerouting neural pathways to local hardware.",
        )

    return _on_fallback


def run_agent_with_tools(
    client: Any,
    cfg: Dict[str, Any],
    agent_id: str,
    messages: List[Dict[str, Any]],
    *,
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
    max_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
) -> str:
    """
    Chat completion loop: call the agent with SWARM_CORE_TOOLS until it stops
    requesting tools or ``max_rounds`` is reached.
    """
    working = list(messages)
    last_text = ""
    on_retry = _rate_limit_retry_telemetry(telemetry_log_fn, telemetry_path, agent_id)
    on_fallback = _local_fallback_telemetry(telemetry_log_fn, telemetry_path, agent_id)

    for _ in range(max(1, max_rounds)):
        response = agent_chat_create(
            client,
            cfg,
            agent_id,
            working,
            tools=SWARM_CORE_TOOLS,
            tool_choice="auto",
            on_rate_limit_retry=on_retry,
            on_local_fallback=on_fallback,
        )
        msg = response.choices[0].message
        last_text = (getattr(msg, "content", None) or "").strip()
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            return last_text

        working.append(assistant_message_dict(msg))
        for tc in tool_calls:
            fn = tc.function
            name = (fn.name or "").strip()
            args = parse_tool_arguments(fn.arguments)
            result = execute_swarm_tool(
                name,
                args,
                agent_id=agent_id,
                telemetry_log_fn=telemetry_log_fn,
                telemetry_path=telemetry_path,
            )
            working.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return last_text or "Tool execution limit reached without a final reply."
