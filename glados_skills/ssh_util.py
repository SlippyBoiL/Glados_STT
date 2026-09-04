# DESCRIPTION: Run a remote command over SSH using paramiko.
# --- GLADOS SKILL: skill_ssh.py ---

import os
import sys
import json
import re
import getpass
from difflib import SequenceMatcher
import socket
import paramiko


def _required_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def _load_devices():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    devices_path = os.path.join(repo, "configs", "devices.yaml")
    try:
        import yaml
    except Exception:
        yaml = None
    if not (yaml and os.path.isfile(devices_path)):
        return {}
    try:
        with open(devices_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        devices = data.get("devices") or {}
        return devices if isinstance(devices, dict) else {}
    except Exception:
        return {}


def _best_device_match(query: str, devices: dict):
    q = (query or "").strip().lower()
    if not q or not devices:
        return None, None

    # Exact key
    if q in devices:
        return q, devices[q]

    # Substring key
    for name, info in devices.items():
        if q in str(name).lower():
            return name, info

    # Fuzzy key
    best = None
    best_score = 0.0
    for name, info in devices.items():
        s = SequenceMatcher(None, q, str(name).lower()).ratio()
        if s > best_score:
            best_score = s
            best = (name, info)
    if best and best_score >= 0.72:
        return best
    return None, None


def _parse_inline_target(text: str):
    """
    Parse "user@1.2.3.4" or "user 1.2.3.4" from free text.
    Returns (user, host) or (None, None).
    """
    if not text:
        return None, None
    m = re.search(r"([a-zA-Z0-9._-]+)\s*@\s*(\d{1,3}(?:\.\d{1,3}){3})", text)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"\buser\s+([a-zA-Z0-9._-]+)\b.*?\b(\d{1,3}(?:\.\d{1,3}){3})\b", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    return None, None


def resolve_target(target: str | None):
    """
    Resolve a target string to connection info.

    - If target contains an IP, use it (optionally with user@ip).
    - Else, match by name from configs/devices.yaml.
    - Else, fall back to SSH_HOST/SSH_USER env vars.
    """
    devices = _load_devices()
    if target:
        user, host = _parse_inline_target(target)
        if host:
            return {"host": host, "user": user}
        name, info = _best_device_match(target, devices)
        if info:
            info = dict(info)
            info.setdefault("name", name)
            return info

    # Env fallback
    return {
        "host": os.environ.get("SSH_HOST", "").strip(),
        "user": os.environ.get("SSH_USER", "").strip(),
        "port": int(os.environ.get("SSH_PORT", "22")),
        "key_path": os.environ.get("SSH_KEY_PATH", "").strip(),
    }


def run_ssh(
    command: str,
    target: str | None = None,
    *,
    interactive: bool = False,
) -> str:
    """
    Env vars:
      SSH_HOST (required)
      SSH_USER (required)
      SSH_PORT (optional, default 22)
      SSH_KEY_PATH (optional)
      SSH_PASSWORD / per-device password_env (optional)

    Never prompts for a password unless interactive=True (CLI only).
    Background monitors must never block the console with getpass.
    """
    resolved = resolve_target(target)
    host = (resolved.get("host") or "").strip()
    user = (resolved.get("user") or "").strip()
    port = int(resolved.get("port") or 22)
    key_path = (resolved.get("key_path") or resolved.get("SSH_KEY_PATH") or "").strip()
    password_env = (resolved.get("password_env") or "").strip()
    password = os.environ.get(password_env, "") if password_env else os.environ.get("SSH_PASSWORD", "")

    if not command or not command.strip():
        return "No command provided."
    if not host:
        return "Missing target host. Provide a device name, an IP, or set SSH_HOST."
    if not user:
        return "Missing SSH user. Provide user@ip / 'user <name> <ip>' or set SSH_USER."

    # Fast preflight: is the SSH port reachable at all?
    try:
        s = socket.create_connection((host, port), timeout=2.5)
        s.close()
    except Exception as e:
        return f"SSH failed: cannot reach {host}:{port} (tcp): {type(e).__name__}: {e}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Avoid long hangs: disable agent/key probing when using password auth.
        kwargs = dict(
            hostname=host,
            username=user,
            port=port,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
            allow_agent=False,
            look_for_keys=bool(key_path),
        )
        if key_path:
            kwargs["key_filename"] = key_path
        elif password:
            kwargs["password"] = password
            kwargs["look_for_keys"] = False
        elif interactive and sys.stdin and sys.stdin.isatty():
            kwargs["password"] = getpass.getpass(f"SSH password for {user}@{host}: ")
            kwargs["look_for_keys"] = False
        else:
            env_hint = password_env or "SSH_PASSWORD"
            return (
                f"SSH failed: no credentials for {user}@{host}:{port} "
                f"(set {env_hint} or SSH key_path — non-interactive mode will not prompt)"
            )

        client.connect(**kwargs)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err and out:
            return out + "\n" + err
        return out or err or "(no output)"
    except paramiko.AuthenticationException:
        return f"SSH failed: authentication rejected for {user}@{host}:{port}"
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        return f"SSH failed: cannot connect to {host}:{port} ({e})"
    except socket.timeout:
        return f"SSH failed: timeout connecting to {host}:{port}"
    except Exception as e:
        return f"SSH failed: {type(e).__name__}: {e}"
    finally:
        client.close()


if __name__ == "__main__":
    # CLI usage:
    #   python -m glados_skills.ssh_util proxmox -- "uname -a"
    if "--" in sys.argv:
        i = sys.argv.index("--")
        tgt = " ".join(sys.argv[1:i]).strip() or None
        cmd = " ".join(sys.argv[i + 1 :]).strip()
    else:
        tgt = None
        cmd = " ".join(sys.argv[1:]).strip()
    try:
        print(run_ssh(cmd, target=tgt, interactive=True))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
