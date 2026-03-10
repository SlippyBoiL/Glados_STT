# DESCRIPTION: Fetches your public IP using ipify API.
# --- GLADOS SKILL: skill_generate_vps_ip.py ---

import socket

try:
    import requests
except ImportError:
    requests = None


def get_public_ip():
    if requests is None:
        return "Install requests: pip install requests"
    try:
        r = requests.get("https://api.ipify.org", timeout=5)
        return r.text.strip()
    except Exception as e:
        return f"Error: {e}"


def main():
    print("Public IP:", get_public_ip())
    print("Local hostname:", socket.gethostname())


if __name__ == "__main__":
    main()
