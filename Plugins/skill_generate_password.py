# DESCRIPTION: Generates a strong random password and prints it once.
# --- GLADOS SKILL: skill_generate_password.py ---

import secrets
import string


def generate_password(length: int = 16) -> str:
    """Generate a strong random password of the given length."""
    if length < 4:
        length = 4

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    password = generate_password(16)
    print(f"Generated password: {password}")


if __name__ == "__main__":
    main()