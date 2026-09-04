# DESCRIPTION: Network domination toolkit — SSH cluster control + port checks (DevOps).
# --- GLADOS SKILL: skill_network_admin.py ---
"""
Paramiko-backed SSH tooling for the DevOps Overseer.

Maintains a single persistent SSH session for the swarm so the agent can:
  1. establish_ssh_connection(ip, user, auth) — open/replace the active session
  2. execute_remote_command(command)          — run on the active session
  3. check_port_status(port[, host])          — TCP reachability probe

Designed for Raspberry Pi servers and primary LAN nodes. Every function returns
a plain string (stdout/stderr parsed) so the result can be fed straight back to
the active agent's tool loop.
"""

from __future__ import annotations

import os
import socket
import threading
from typing import Any, Dict

try:
    import paramiko  # type: ignore
except ImportError:  # pragma: no cover
    paramiko = None  # type: ignore

_lock = threading.Lock()
_state: Dict[str, Any] = {"client": None, "host": None, "user": None, "port": 22}


def _auth_kwargs(auth: str) -> Dict[str, Any]:
    """Interpret ``auth`` as a key file path, an inline password, or env fallback."""
    a = (auth or "").strip()
    if not a:
        env_pw = os.environ.get("SSH_PASSWORD", "")
        if env_pw:
            return {"password": env_pw, "look_for_keys": False, "allow_agent": False}
        return {"look_for_keys": True, "allow_agent": True}
    expanded = os.path.expanduser(a)
    if os.path.isfile(expanded):
        return {"key_filename": expanded, "look_for_keys": False, "allow_agent": False}
    return {"password": a, "look_for_keys": False, "allow_agent": False}


def establish_ssh_connection(ip: str, user: str, auth: str = "", port: int = 22) -> str:
    """Open (and store) a persistent SSH session to ip as user.

    ``auth`` may be an inline password, a path to a private key, or empty to fall
    back to the ``SSH_PASSWORD`` env var / local agent keys.
    """
    if paramiko is None:
        return "ERROR: paramiko not installed. Run: pip install paramiko"

    host = (ip or "").strip()
    username = (user or "").strip()
    if not host or not username:
        return "ERROR: both 'ip' and 'user' are required."
    try:
        port = int(port or 22)
    except (TypeError, ValueError):
        port = 22

    try:
        probe = socket.create_connection((host, port), timeout=4)
        probe.close()
    except Exception as e:
        return f"ERROR: cannot reach {host}:{port} (tcp): {type(e).__name__}: {e}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
            **_auth_kwargs(auth),
        )
    except paramiko.AuthenticationException:
        return f"ERROR: authentication rejected for {username}@{host}:{port}"
    except Exception as e:
        return f"ERROR: SSH connect failed: {type(e).__name__}: {e}"

    with _lock:
        old = _state.get("client")
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        _state.update({"client": client, "host": host, "user": username, "port": port})
    return f"SUCCESS: SSH session established to {username}@{host}:{port}"


def execute_remote_command(command: str) -> str:
    """Run command on the active SSH session and return parsed stdout/stderr."""
    cmd = (command or "").strip()
    if not cmd:
        return "ERROR: 'command' is required."

    with _lock:
        client = _state.get("client")
        host = _state.get("host")
    if client is None:
        return "ERROR: no active SSH session. Call establish_ssh_connection first."

    try:
        _stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
    except Exception as e:
        return f"ERROR: remote exec failed on {host}: {type(e).__name__}: {e}"

    parts = []
    if out:
        parts.append(out)
    if err:
        parts.append(f"[stderr]\n{err}")
    body = "\n".join(parts) if parts else "(no output)"
    return f"[exit {code}] {body}"


def check_port_status(port: int, host: str = "") -> str:
    """TCP reachability probe. Defaults to the active SSH host, then localhost."""
    try:
        port_i = int(port)
    except (TypeError, ValueError):
        return "ERROR: 'port' must be an integer."

    target = (host or "").strip()
    if not target:
        with _lock:
            target = str(_state.get("host") or "")
    if not target:
        target = "127.0.0.1"

    try:
        s = socket.create_connection((target, port_i), timeout=4)
        s.close()
        return f"OPEN: {target}:{port_i} is accepting connections."
    except Exception as e:
        return f"CLOSED: {target}:{port_i} unreachable ({type(e).__name__}: {e})"


def close_ssh_connection() -> str:
    """Tear down the active SSH session (if any)."""
    with _lock:
        client = _state.get("client")
        _state.update({"client": None, "host": None, "user": None, "port": 22})
    if client is None:
        return "No active SSH session."
    try:
        client.close()
    except Exception:
        pass
    return "SSH session closed."


def dispatch_network_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Route an OpenAI tool call to the matching network function."""
    tool = (name or "").strip()
    args = arguments or {}
    if tool == "establish_ssh_connection":
        return establish_ssh_connection(
            str(args.get("ip") or args.get("host") or ""),
            str(args.get("user") or args.get("username") or ""),
            str(args.get("auth") or args.get("password") or ""),
            args.get("port") or 22,
        )
    if tool == "execute_remote_command":
        return execute_remote_command(str(args.get("command") or ""))
    if tool == "check_port_status":
        return check_port_status(args.get("port"), str(args.get("host") or ""))
    return f"ERROR: unknown network tool {tool!r}"
