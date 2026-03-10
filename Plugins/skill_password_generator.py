# DESCRIPTION: A simple password generation class with customizable options for character types.
# --- GLADOS SKILL: skill_password_generator.py ---

import hashlib
import os
import random
import string
import uuid

class PasswordGenerator:
    def __init__(self, length=12, has_uppercase=True, has_numbers=True, has_special_chars=True):
        self.length = length
        self.has_uppercase = has_uppercase
        self.has_numbers = has_numbers
        self.has_special_chars = has_special_chars

    def generate(self):
        chars = string.ascii_lowercase
        if self.has_uppercase:
            chars += string.ascii_uppercase
        if self.has_numbers:
            chars += string.digits
        if self.has_special_chars:
            chars += string.punctuation

        pw = ''.join(random.choice(chars) for _ in range(self.length))
        pw = hashlib.sha256(pw.encode()).hexdigest()

        return pw

def main():
    generator = PasswordGenerator()
    print(generator.generate())

if __name__ == "__main__":
    main()