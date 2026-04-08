# DESCRIPTION: Run a remote command over SSH using paramiko.
# --- GLADOS SKILL: skill_ssh.py ---

import os
import sys
import json
import paramiko


def _required_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def run_ssh(command: str) -> str:
    """
    Env vars:
      SSH_HOST (required)
      SSH_USER (required)
      SSH_PORT (optional, default 22)
      SSH_KEY_PATH (optional)
      SSH_PASSWORD (optional; not recommended)
    """
    host = _required_env("SSH_HOST")
    user = _required_env("SSH_USER")
    port = int(os.environ.get("SSH_PORT", "22"))
    key_path = os.environ.get("SSH_KEY_PATH", "").strip()
    password = os.environ.get("SSH_PASSWORD", "")

    if not command or not command.strip():
        return "No command provided."

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        kwargs = dict(hostname=host, username=user, port=port, timeout=10)
        if key_path:
            kwargs["key_filename"] = key_path
        elif password:
            kwargs["password"] = password

        client.connect(**kwargs)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err and out:
            return out + "\n" + err
        return out or err or "(no output)"
    finally:
        client.close()


if __name__ == "__main__":
    # CLI usage: python plugins/skill_ssh.py "whoami"
    cmd = " ".join(sys.argv[1:]).strip()
    try:
        print(run_ssh(cmd))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
