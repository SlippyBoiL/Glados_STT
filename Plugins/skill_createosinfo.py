# DESCRIPTION: Prints OS name, hostname, and basic system info.
# --- GLADOS SKILL: skill_createosinfo.py ---

import platform
import socket
import secrets

try:
    import psutil
except ImportError:
    psutil = None


def get_osinfo():
    info = {
        "OS": platform.system(),
        "Release": platform.release(),
        "Machine": platform.machine(),
        "Hostname": socket.gethostname(),
    }
    if psutil:
        info["CPUs"] = psutil.cpu_count()
        info["Memory %"] = f"{psutil.virtual_memory().percent}%"
        try:
            info["CPU MHz"] = psutil.cpu_freq().current if psutil.cpu_freq() else "N/A"
        except Exception:
            info["CPU MHz"] = "N/A"
    return info


def main():
    for k, v in get_osinfo().items():
        print(f"{k}: {v}")
    print(f"Token: {secrets.token_hex(16)}")


if __name__ == "__main__":
    main()
