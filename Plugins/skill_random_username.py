# DESCRIPTION: Generates a random username and prints it once.
# --- GLADOS SKILL: skill_random_username.py ---

import random
import string


def generate_username(length: int = 8) -> str:
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def main() -> None:
    username = generate_username(10)
    print(f"Generated random username: {username}")


if __name__ == "__main__":
    main()