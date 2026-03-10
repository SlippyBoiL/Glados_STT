# DESCRIPTION: Checks if a hostname resolves (e.g. DNS/HTTP).
# --- GLADOS SKILL: skill_wait_for_service.py ---

import socket
import time


def check_host(hostname, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(hostname)
        return True
    except (socket.gaierror, OSError):
        return False


def main():
    for name in ["google.com", "github.com"]:
        ok = check_host(name)
        print(f"{name}: {'reachable' if ok else 'not reachable'}")


if __name__ == "__main__":
    main()
