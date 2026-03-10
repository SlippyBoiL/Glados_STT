# DESCRIPTION: Generates a hash-based identifier for a file (SHA-256 + base64).
# --- GLADOS SKILL: skill_generate_encrypted_file_path.py ---

import hashlib
import base64
import os


def generate_encrypted_file_path(file_name):
    if not os.path.exists(file_name):
        return f"(file not found: {file_name})"
    with open(file_name, "rb") as f:
        file_hash = hashlib.sha256(f.read()).digest()
    encoded = base64.b64encode(file_hash).decode("utf-8")[:16]
    return f"{encoded}_{os.path.basename(file_name)}"


def main():
    # Demo: use this script's path
    path = __file__
    result = generate_encrypted_file_path(path)
    print(f"Hash path for current script: {result}")


if __name__ == "__main__":
    main()
