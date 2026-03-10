# DESCRIPTION: Generates a ransom-note style message (practice/novelty only).
# --- GLADOS SKILL: skill_ransom_note_generator.py ---

import random
import string


def generate_ransom_note(message="your data", length=80):
    chars = string.ascii_letters + string.digits
    random_part = "".join(random.choice(chars) for _ in range(length))
    return f"Your {message} has been taken! Instructions: {random_part}"


def main():
    note = generate_ransom_note("attention", 60)
    print(note)


if __name__ == "__main__":
    main()
