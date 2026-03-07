# DESCRIPTION: This script generates a ransom note with random characters and a custom message, suitable for practice purposes.
# --- GLADOS SKILL: skill_ransom_note_generator.py ---

# skill_ransom_note_generator.py

import random
import string

def generate_ransom_note(text):
    """Generate a ransom note with random characters and a fixed message."""
    characters = string.ascii_letters + string.digits
    note = ''.join(random.choice(characters) for _ in range(100))
    message = f"Your {text} has been taken! Read the following note for instructions: {note}"
    return message

def generate_ransom_text(length):
    """Generate a random ransom text."""
    text = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    return text

def print_ransom_note(text, length):
    """Print a ransom note."""
    ransom_note = generate_ransom_note(text)
    print(" ransom note:")
    print(ransom_note)

    random_text = generate_ransom_text(length)
    print(f"Random Text: {random_text}")

# Usage
def main():
    text = input("Enter a text to generate a ransom note for: ")
    length = int(input("Enter the length of the random text: "))
    print_ransom_note(text, length)

if __name__ == "__main__":
    main()

This script, `skill_ransom_note_generator.py`, provides a utility to generate a ransom note with a random character mix. The `generate_ransom_note` function generates a ransom note message, and `generate_ransom_text` generates a random ransom text. The `print_ransom_note` function prints both the ransom note and the random text. The `main` function takes a text and a length as input, and uses them to generate a ransom note.