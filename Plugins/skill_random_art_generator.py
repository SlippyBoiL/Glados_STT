# DESCRIPTION: Generates a small random ASCII art and prints it.
# --- GLADOS SKILL: skill_random_art_generator.py ---

import random
import string


def generate_random_art(width=40, height=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "\n".join(
        "".join(random.choice(chars) for _ in range(width))
        for _ in range(height)
    )


def main():
    art = generate_random_art()
    print(art)


if __name__ == "__main__":
    main()
