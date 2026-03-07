# DESCRIPTION: Quickly prints a simple random password.
# --- GLADOS SKILL: skill_random_password.py ---

import secrets
import string


def generate_random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    password = generate_random_password(12)
    print(f"Generated password: {password}")


if __name__ == "__main__":
    main()