"""Local PC control via Hermes tool-calling (no Open Interpreter / litellm)."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, Dict, List, Optional

from glados_skills.swarm_tools import assistant_message_dict, parse_tool_arguments

StreamFn = Callable[[str, bool], None]

HANDS_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "execute_powershell",
            "description": (
                "Run PowerShell on this Windows PC. Use for apps, files, git, "
                "processes, and system checks. One focused command per call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Exact PowerShell to run.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_windows_app",
            "description": (
                "Open or close an application on this Windows PC "
                "(Chrome, Discord, Steam, Notepad, Explorer, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open", "close"],
                    },
                    "app": {
                        "type": "string",
                        "description": "App name, e.g. chrome, discord, steam, notepad.",
                    },
                },
                "required": ["action", "app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": "Read a text file on this PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to read."}
                },
                "required": ["file_path"],
            },
        },
    },
]

_MAX_TOOL_ROUNDS = 6
_MAX_FILE_CHARS = 12000


def _auto_confirm() -> bool:
    return os.environ.get("GLADOS_OI_AUTO_CONFIRM", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _run_powershell(script: str, *, timeout: int = 60) -> str:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=os.getcwd(),
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    lines = [f"exit={proc.returncode}"]
    if out:
        lines.append(out)
    if err:
        lines.append(err)
    return "\n".join(lines)[:8000]


def _gated_powershell(script: str) -> str:
    script = (script or "").strip()
    if not script:
        return "empty command"
    import sys
    from glados_paths import REPO_ROOT, resolve_plugins_dir
    for folder in (resolve_plugins_dir(), os.path.join(REPO_ROOT, "Plugins"), os.path.join(REPO_ROOT, "plugins"), REPO_ROOT):
        if folder and folder not in sys.path:
            sys.path.insert(0, folder)
    from capability_gate import intercept_powershell  # type: ignore
    ok, report = intercept_powershell(
        script,
        auto_confirm=_auto_confirm(),
        run_fn=_run_powershell,
    )
    return report if report else ("ok" if ok else "blocked")


def _read_file(path: str) -> str:
    path = os.path.expandvars(os.path.expanduser((path or "").strip().strip('"')))
    if not path:
        return "No path given."
    if not os.path.isfile(path):
        return f"Not a file: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = fh.read(_MAX_FILE_CHARS + 1)
    except OSError as exc:
        return f"Read failed: {exc}"
    if len(data) > _MAX_FILE_CHARS:
        return data[:_MAX_FILE_CHARS] + "\n…[truncated]"
    return data or "(empty file)"


def _control_app(action: str, app: str) -> str:
    action = (action or "open").strip().lower()
    app = (app or "").strip()
    if not app:
        return "No app name given."
    try:
        import sys
        from glados_paths import REPO_ROOT, resolve_plugins_dir

        for folder in (
            resolve_plugins_dir(),
            os.path.join(REPO_ROOT, "Plugins"),
            os.path.join(REPO_ROOT, "plugins"),
            REPO_ROOT,
        ):
            if folder and folder not in sys.path:
                sys.path.insert(0, folder)
        from skill_windows_apps import close_app, open_app  # type: ignore
    except Exception as exc:
        return f"Windows app skill unavailable: {exc}"
    if action == "close":
        ok, detail = close_app(app)
        return f"close {'ok' if ok else 'fail'}: {detail}"
    ok, detail = open_app(app)
    return f"open {'ok' if ok else 'fail'}: {detail}"


def dispatch_hands_tool(name: str, arguments: Dict[str, Any]) -> str:
    n = (name or "").strip()
    if n == "execute_powershell":
        return _gated_powershell(str(arguments.get("command") or ""))
    if n == "read_local_file":
        return _read_file(str(arguments.get("file_path") or arguments.get("path") or ""))
    if n == "control_windows_app":
        return _control_app(
            str(arguments.get("action") or "open"),
            str(arguments.get("app") or arguments.get("name") or ""),
        )
    return f"Unknown tool {n!r}"


def run_hands_loop(
    client: Any,
    model_name: str,
    messages: List[Dict[str, Any]],
    completion_kwargs: Optional[Dict[str, Any]] = None,
    *,
    think_fn: Optional[Callable[..., None]] = None,
    max_rounds: int = _MAX_TOOL_ROUNDS,
) -> str:
    """Hermes native tools until the model speaks a final reply."""
    working: List[Dict[str, Any]] = list(messages)
    kw = dict(completion_kwargs or {})
    kw.pop("stream", None)
    last = ""

    def _think(msg: str) -> None:
        if not think_fn:
            return
        try:
            think_fn("execute", msg[:300])
        except Exception:
            pass

    for _ in range(max(1, max_rounds)):
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=working,
                tools=HANDS_TOOLS,
                tool_choice="auto",
                **kw,
            )
        except Exception as extra:
            from glados_llm import is_llm_connection_error

            if "extra_body" in kw and not is_llm_connection_error(extra):
                kw.pop("extra_body", None)
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=working,
                    tools=HANDS_TOOLS,
                    tool_choice="auto",
                    **kw,
                )
            else:
                raise extra
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        content = (getattr(msg, "content", None) or "").strip()
        if content:
            last = content
        if not tool_calls:
            break
        working.append(assistant_message_dict(msg))
        for tc in tool_calls:
            fn = getattr(tc, "function", None)
            name = getattr(fn, "name", "") if fn else ""
            args = parse_tool_arguments(getattr(fn, "arguments", None) if fn else None)
            _think(f"tool {name}")
            result = dispatch_hands_tool(name, args)
            working.append(
                {
                    "role": "tool",
                    "tool_call_id": getattr(tc, "id", "") or name,
                    "content": result[:8000],
                }
            )
    if last:
        try:
            from glados_think import split_think_speak

            _thinking, spoken = split_think_speak(last, "")
            return (spoken or last).strip()
        except Exception:
            return last
    return last