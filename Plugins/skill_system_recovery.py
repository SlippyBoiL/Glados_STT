# DESCRIPTION: Windows process recovery tools for the Maintenance Agent.
# --- GLADOS SKILL: skill_system_recovery.py ---

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, Optional

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None  # type: ignore


def _normalize_process_name(process_name: str) -> str:
    name = (process_name or "").strip()
    if not name:
        return ""
    if not name.lower().endswith(".exe"):
        name = f"{name}.exe"
    return name


def kill_process(process_name: str) -> Dict[str, Any]:
    """
    Force-terminate a Windows process by image name (taskkill /F /IM).
    Returns a structured result dict — never raises.
    """
    exe = _normalize_process_name(process_name)
    if not exe:
        return {"ok": False, "error": "process_name is required"}

    try:
        proc = subprocess.run(
            ["taskkill", "/F", "/IM", exe],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode in (0, 128)  # 128 = no matching tasks (already dead)
        return {
            "ok": ok,
            "process_name": exe,
            "returncode": proc.returncode,
            "output": out.strip(),
        }
    except Exception as exc:
        return {"ok": False, "process_name": exe, "error": str(exc)}


def verify_process_active(process_name: str) -> Dict[str, Any]:
    """Return whether any matching process is running (psutil task list)."""
    exe = _normalize_process_name(process_name)
    if not exe:
        return {"ok": False, "active": False, "error": "process_name is required"}

    if psutil is None:
        return {"ok": False, "active": False, "error": "psutil not installed"}

    target = exe.lower()
    pids: list[int] = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name == target:
                    pids.append(int(proc.info["pid"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {
            "ok": True,
            "process_name": exe,
            "active": bool(pids),
            "pids": pids,
            "count": len(pids),
        }
    except Exception as exc:
        return {"ok": False, "active": False, "process_name": exe, "error": str(exc)}


def relaunch_application(app_path: str, *, wait_sec: float = 2.0) -> Dict[str, Any]:
    """
    Launch a clean application instance via os.startfile (Windows) or subprocess.Popen.
    """
    path = (app_path or "").strip()
    if not path:
        return {"ok": False, "error": "app_path is required"}

    path = os.path.expanduser(path)
    try:
        if os.name == "nt" and os.path.isfile(path):
            os.startfile(path)  # type: ignore[attr-defined]
            pid: Optional[int] = None
        else:
            proc = subprocess.Popen(
                path if os.path.isfile(path) else path.split(),
                shell=not os.path.isfile(path),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if os.name == "nt" and not os.path.isfile(path)
                else 0,
            )
            pid = proc.pid

        if wait_sec > 0:
            time.sleep(wait_sec)

        return {"ok": True, "app_path": path, "pid": pid}
    except Exception as exc:
        return {"ok": False, "app_path": path, "error": str(exc)}
