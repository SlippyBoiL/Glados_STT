# DESCRIPTION: Generates a secret key and password hash.
# --- GLADOS SKILL: skill_generate_secret_key.py ---

import hashlib
import secrets
import socket


def get_public_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def main():
    print("Secret key:", secrets.token_urlsafe(24))
    pwd = secrets.token_urlsafe(12)
    print("Sample password hash (SHA-256):", hashlib.sha256(pwd.encode()).hexdigest())
    print("Public IP:", get_public_ip())


if __name__ == "__main__":
    main()
