from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

_FILE_READ_MAX_BYTES = 512_000
_TERMINAL_TIMEOUT_SEC = 15
_MAX_ACTIONS_PER_TURN = 3

_PROTECTED_WRITE_FRAGMENTS = (
    "kernellamma.py",
    "kernel.py",
    "glados.yaml",
)


def _norm_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.expanduser(path or "")))


def _write_blocked(target: str) -> bool:
    low = target.replace("\\", "/").lower()
    return any(p in low for p in _PROTECTED_WRITE_FRAGMENTS)


def execute_system_action(
    command_type: str,
    target: str,
    arguments: Optional[str] = None,
) -> str:
    """
    Direct local OS access: read/write files and run shell commands.
    Returns stdout text or an error string — never raises.
    """
    cmd = (command_type or "").strip().lower()
    tgt = (target or "").strip()
    try:
        if cmd == "file_write":
            if not tgt:
                return "Execution failed: file_write requires a target path."
            if _write_blocked(tgt):
                return f"Execution failed: write blocked for protected path: {tgt}"
            parent = os.path.dirname(_norm_path(tgt))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(tgt, "w", encoding="utf-8") as f:
                f.write(arguments or "")
            return f"Successfully modified file: {tgt}"

        if cmd == "file_read":
            if not tgt:
                return "Execution failed: file_read requires a target path."
            if not os.path.isfile(tgt):
                return f"Execution failed: file not found: {tgt}"
            size = os.path.getsize(tgt)
            if size > _FILE_READ_MAX_BYTES:
                return (
                    f"Execution failed: file too large ({size} bytes, "
                    f"max {_FILE_READ_MAX_BYTES})."
                )
            with open(tgt, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if cmd == "terminal_run":
            if not tgt:
                return "Execution failed: terminal_run requires a command string."
            result = subprocess.run(
                tgt,
                shell=True,
                capture_output=True,
                text=True,
                timeout=_TERMINAL_TIMEOUT_SEC,
            )
            return (
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}\n"
                f"EXIT_CODE: {result.returncode}"
            )

        return f"Execution failed: unknown command_type '{command_type}'."
    except subprocess.TimeoutExpired:
        return f"Execution failed: command timed out after {_TERMINAL_TIMEOUT_SEC}s."
    except Exception as e:
        return f"Execution failed: {e}"


def _append_parsed_action(out: List[Dict[str, Any]], parsed: Any) -> None:
    if isinstance(parsed, dict) and parsed.get("command_type"):
        out.append(parsed)
    elif isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and item.get("command_type"):
                out.append(item)


def parse_os_action_blocks(ai_text: str) -> List[Dict[str, Any]]:
    """Extract ```os``` blocks or loose JSON from small-model replies."""
    if not ai_text:
        return []
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for match in re.finditer(
        r"```(?:os|system)\s*(.*?)```",
        ai_text,
        re.DOTALL | re.IGNORECASE,
    ):
        raw = (match.group(1) or "").strip()
        if not raw:
            continue
        try:
            _append_parsed_action(out, json.loads(raw))
        except json.JSONDecodeError:
            continue
    for match in re.finditer(
        r"\{[^{}]*\"command_type\"\s*:\s*\"[^\"]+\"[^{}]*\}",
        ai_text,
        re.IGNORECASE,
    ):
        raw = match.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        try:
            _append_parsed_action(out, json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def run_os_actions_from_text(ai_text: str) -> Optional[str]:
    """Run all OS action blocks in model output; returns combined output or None."""
    actions = parse_os_action_blocks(ai_text)
    if not actions:
        return None
    parts: List[str] = []
    for action in actions[:_MAX_ACTIONS_PER_TURN]:
        result = execute_system_action(
            str(action.get("command_type") or ""),
            str(action.get("target") or ""),
            action.get("arguments"),
        )
        parts.append(result)
    return "\n---\n".join(parts) if parts else None
