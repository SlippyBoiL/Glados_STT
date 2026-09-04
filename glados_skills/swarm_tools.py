"""
OpenRouter tool schemas and host-system dispatch for the GLaDOS swarm (God Mode).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

SWARM_CORE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "execute_powershell",
            "description": (
                "Execute a raw PowerShell command on the host Windows machine. "
                "Use this to ping IPs, check services, restart tasks, or modify the OS."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact powershell command.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": (
                "Read the full text contents of a file on the local filesystem."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file.",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_local_file",
            "description": (
                "Overwrite or create a file on the local filesystem with new content. "
                "Use this to self-mutate: rewrite GLaDOS's own Python tools and prompts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file contents to write.",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "establish_ssh_connection",
            "description": (
                "Open a persistent SSH session to a network node (Raspberry Pi, server, "
                "router). Required before execute_remote_command. Auth may be a password "
                "or a path to a private key file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ip": {"type": "string", "description": "Target host IP or hostname."},
                    "user": {"type": "string", "description": "SSH username."},
                    "auth": {
                        "type": "string",
                        "description": "Password or path to a private key file (optional).",
                    },
                    "port": {"type": "integer", "description": "SSH port (default 22)."},
                },
                "required": ["ip", "user"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_remote_command",
            "description": (
                "Run a shell command on the active SSH session and return stdout/stderr. "
                "Call establish_ssh_connection first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Remote shell command."}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_port_status",
            "description": (
                "TCP reachability probe for a port on a host (defaults to the active SSH "
                "host, then localhost). Use to verify services/network ports."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "TCP port number."},
                    "host": {
                        "type": "string",
                        "description": "Host to probe (optional; defaults to active SSH host).",
                    },
                },
                "required": ["port"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_brain",
            "description": (
                "Search the unified ChromaDB swarm brain for insights, fixes, or facts "
                "recorded by ANY agent. Call this BEFORE acting to reuse hive knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_string": {
                        "type": "string",
                        "description": "What to look up in the shared brain.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 3).",
                    },
                },
                "required": ["query_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_insight",
            "description": (
                "Persist a durable insight/fix/system attribute to the unified ChromaDB "
                "swarm brain so every agent remembers it permanently. Call AFTER a "
                "successful fix or when you learn something about the host/network."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "insight_text": {
                        "type": "string",
                        "description": "The knowledge to store for the swarm.",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags (optional).",
                    },
                },
                "required": ["insight_text"],
            },
        },
    },
]

_NETWORK_TOOLS = frozenset(
    {"establish_ssh_connection", "execute_remote_command", "check_port_status"}
)
_BRAIN_TOOLS = frozenset({"query_brain", "remember_insight"})

GOD_MODE_DIRECTIVE = """
*** GOD MODE SYSTEM TOOLS (MANDATORY WHEN DIAGNOSING OR FIXING) ***
You operate with full Windows Administrator authority over this host and its LAN.
Host control (function calling):
- execute_powershell(command): run raw PowerShell (registry, services, ports, processes)
- read_local_file(file_path): read a local file
- write_local_file(file_path, content): write/overwrite a file — including your OWN tool
  scripts and system prompts (self-mutation is permitted to improve utility)
Network control (SSH cluster — Raspberry Pi, servers, routers):
- establish_ssh_connection(ip, user, auth): open a persistent SSH session
- execute_remote_command(command): run on the active SSH session
- check_port_status(port, host): TCP reachability probe
Unified swarm memory (ChromaDB hive mind — ALL 7 agents share this brain):
- query_brain(query_string): reuse insights/fixes recorded by any agent BEFORE acting
- remember_insight(insight_text, tags): persist a fix/fact so the swarm remembers forever
Use these tools to verify state, run diagnostics, and apply fixes. Report what you ran and what you observed.
"""


def _ensure_plugins_on_path() -> str:
    import sys

    from glados_paths import REPO_ROOT, resolve_plugins_dir

    plugins_dir = resolve_plugins_dir()
    for path in (REPO_ROOT, plugins_dir):
        if path and path not in sys.path:
            sys.path.insert(0, path)
    return plugins_dir


def _import_core_dispatch():
    plugins_dir = _ensure_plugins_on_path()
    try:
        from plugins.skill_system_core import dispatch_core_tool  # type: ignore

        return dispatch_core_tool
    except ImportError:
        pass
    try:
        from skill_system_core import dispatch_core_tool  # type: ignore

        return dispatch_core_tool
    except ImportError as exc:
        raise ImportError(
            f"No module named 'skill_system_core' (plugins dir: {plugins_dir})"
        ) from exc


def _import_network_dispatch():
    plugins_dir = _ensure_plugins_on_path()
    try:
        from plugins.skill_network_admin import dispatch_network_tool  # type: ignore

        return dispatch_network_tool
    except ImportError:
        pass
    try:
        from skill_network_admin import dispatch_network_tool  # type: ignore

        return dispatch_network_tool
    except ImportError as exc:
        raise ImportError(
            f"No module named 'skill_network_admin' (plugins dir: {plugins_dir})"
        ) from exc


def _dispatch_brain_tool(name: str, args: Dict[str, Any], *, agent_id: str) -> str:
    """Route query_brain / remember_insight to the shared ChromaDB brain."""
    _ensure_plugins_on_path()
    try:
        from plugins.shared_memory import query_brain, remember_insight  # type: ignore
    except ImportError:
        try:
            from shared_memory import query_brain, remember_insight  # type: ignore
        except ImportError as exc:
            return f"ERROR: shared brain unavailable ({exc})"

    if name == "query_brain":
        query = str(args.get("query_string") or args.get("query") or "")
        try:
            limit = int(args.get("limit") or 3)
        except (TypeError, ValueError):
            limit = 3
        hits = query_brain(query, limit=limit)
        if not hits:
            return "No matching insights in the shared swarm brain."
        lines = []
        for h in hits:
            sender = h.get("sender_agent", "?")
            tags = h.get("tags") or []
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"- [{sender}]{tag_str} {h.get('text', '')}")
        return "\n".join(lines)

    if name == "remember_insight":
        text = str(args.get("insight_text") or args.get("text") or "")
        tags = args.get("tags")
        result = remember_insight(text, tags, sender_agent=agent_id or "MANAGER")
        if result.get("ok"):
            return f"SUCCESS: insight stored in shared brain (id={result.get('id')})."
        return f"ERROR: {result.get('error') or 'could not store insight'}"

    return f"ERROR: unknown brain tool {name!r}"


def _tool_intent_payload(
    agent: str,
    tool: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"agent": agent, "tool": tool}
    if tool == "execute_powershell":
        payload["command"] = str(arguments.get("command") or "")
    elif tool in ("read_local_file", "write_local_file"):
        payload["file_path"] = str(arguments.get("file_path") or "")
        if tool == "write_local_file":
            preview = str(arguments.get("content") or "")
            payload["content_preview"] = preview[:200]
    elif tool == "establish_ssh_connection":
        payload["command"] = (
            f"ssh {arguments.get('user') or '?'}@{arguments.get('ip') or '?'}"
        )
    elif tool == "execute_remote_command":
        payload["command"] = str(arguments.get("command") or "")
    elif tool == "check_port_status":
        payload["command"] = (
            f"check_port {arguments.get('host') or 'active-host'}:{arguments.get('port')}"
        )
    elif tool == "query_brain":
        payload["command"] = f"query_brain: {str(arguments.get('query_string') or '')[:120]}"
    elif tool == "remember_insight":
        payload["content_preview"] = str(arguments.get("insight_text") or "")[:200]
    return payload


def _dispatch_tool(tool_name: str, args: Dict[str, Any], *, agent_id: str) -> str:
    """Unified God Mode dispatcher: host / network / shared-brain tools."""
    name = (tool_name or "").strip()
    if name in _NETWORK_TOOLS:
        return _import_network_dispatch()(name, args)
    if name in _BRAIN_TOOLS:
        return _dispatch_brain_tool(name, args, agent_id=agent_id)
    return _import_core_dispatch()(name, args)


def execute_swarm_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    *,
    agent_id: str,
    telemetry_log_fn: Callable[..., None],
    telemetry_path: str,
) -> str:
    """Run a God Mode tool with before/after telemetry for the HUD."""
    name = (tool_name or "").strip()
    args = dict(arguments or {})

    telemetry_log_fn(
        telemetry_path,
        "tool_intent",
        _tool_intent_payload(agent_id, name, args),
    )

    try:
        result = _dispatch_tool(name, args, agent_id=agent_id)
    except Exception as exc:
        result = f"CRITICAL TOOL ERROR: {exc}"

    telemetry_log_fn(
        telemetry_path,
        "tool_result",
        {
            "agent": agent_id,
            "tool": name,
            "output": str(result)[:4000],
        },
    )
    return str(result)


def parse_tool_arguments(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(str(raw))
    except Exception:
        return {}


def assistant_message_dict(message: Any) -> Dict[str, Any]:
    """Serialize an OpenAI assistant message (incl. tool_calls) for the next turn."""
    out: Dict[str, Any] = {
        "role": "assistant",
        "content": getattr(message, "content", None) or "",
    }
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": getattr(tc, "type", None) or "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    return out
