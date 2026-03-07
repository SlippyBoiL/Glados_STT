# DESCRIPTION: One-shot password generator with configurable options.
# --- GLADOS SKILL: skill_password_generator.py ---

import random
import string


class PasswordGenerator:
    def __init__(self, length: int = 16, include_special: bool = True) -> None:
        self.length = max(4, length)
        self.include_special = include_special

    def generate(self) -> str:
        characters = string.ascii_letters + string.digits
        if self.include_special:
            characters += string.punctuation
        return "".join(random.choice(characters) for _ in range(self.length))


def main() -> None:
    generator = PasswordGenerator(length=16, include_special=True)
    password = generator.generate()
    print(f"Generated password: {password}")


if __name__ == "__main__":
    main()