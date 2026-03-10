# DESCRIPTION: Generates a random password length between `min_length` and `max_length` with a default of 20.
# --- GLADOS SKILL: skill_password_length.py ---

#!/usr/bin/env python3

import time
import random
import string

def generate_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

def create_password_file(password):
    with open("password.txt", "w") as file:
        file.write(password)

def generate_password_length_function(min_length, max_length, default_length=20):
    return random.randint(min_length, max_length)

class PasswordManager:
    def __init__(self, password_file="password.txt"):
        self.password_file = password_file

    def get_password(self):
        try:
            with open(self.password_file, "r") as file:
                return file.read()
        except FileNotFoundError:
            return None

    def update_password(self, password):
        with open(self.password_file, "w") as file:
            file.write(password)

def main():
    password_manager = PasswordManager()
    if password_manager.get_password() is None:
        length = generate_password_length_function(12, 30)
        password = generate_password(length)
        create_password_file(password)
        print(f"Password generated and saved to password.txt")

    new_password_generator = generate_password_length_function
    password = new_password_generator(20, 40)
    print(f"Generated password: {password}")
    password_manager.update_password(password)

if __name__ == "__main__":
    while True:
        time.sleep(random.randint(10, 60))
        main()