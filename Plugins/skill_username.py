# DESCRIPTION: Prints current user and system info.
# --- GLADOS SKILL: skill_username.py ---

import platform
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_user_info():
    lines = [
        f"Username: {os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))}",
        f"Computer: {platform.node()}",
        f"OS: {platform.system()} {platform.release()}",
        f"Python: {platform.python_version()}",
    ]
    if HAS_PSUTIL:
        lines.append(f"RAM usage: {psutil.virtual_memory().percent}%")
        lines.append(f"CPU: {psutil.cpu_percent()}%")
    lines.append(f"Home: {os.path.expanduser('~')}")
    return "\n".join(lines)


def main():
    print(get_user_info())


if __name__ == "__main__":
    main()
