# DESCRIPTION: Hash a password with SHA-256 (or generate a random one and hash it).
# --- GLADOS SKILL: skill_hashing.py ---

import hashlib
import random
import string


def generate_password(length=16):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def main():
    password = generate_password(12)
    hashed = hashlib.sha256(password.encode()).hexdigest()
    print(f"Generated password (do not use in production): {password}")
    print(f"SHA-256 hash: {hashed}")


if __name__ == "__main__":
    main()
