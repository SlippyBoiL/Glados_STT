# DESCRIPTION: A Python class designed to generate random passwords of varying lengths with customizable options for special characters, uppercase, and numbers.
# --- GLADOS SKILL: skill_password_generator.py ---

#!/usr/bin/python
import os
import sys
import binascii
import random
import string
import time

class PasswordGenerator:
    def __init__(self, length=12, include_special=False, include_uppercase=True, include_numbers=True):
        self.length = length
        self.include_special = include_special
        self.include_uppercase = include_uppercase
        self.include_numbers = include_numbers

    def generate(self):
        characters = string.ascii_lowercase
        if self.include_uppercase:
            characters += string.ascii_uppercase
        if self.include_numbers:
            characters += string.digits
        if self.include_special:
            characters += string.punctuation

        password = ''.join(random.choice(characters) for i in range(self.length))
        return password

def main():
    length = 12
    include_email_format = False
    include_password = True
    include_phone_format = False
    include_suffixes = False

    while True:
        print("1. Generate Password")
        print("2. Generate Phone Number")
        print("3. Generate Email Address")
        print("4. Generate First/Last Name Suffixes")
        try:
            choice = int(input("Choose a option: "))
        except:
            print("Invalid Choice")
            continue

        if choice == 1:
            include_password = True
            include_email_format = False
            include_phone_format = False
            include_suffixes = False
            password_generator = PasswordGenerator(length=16, include_uppercase=True, include_numbers=True)
            password = password_generator.generate()
            print(f"Generated Password: {password}")

        elif choice == 2:
            include_phone_format = True
            include_email_format = False
            include_password = False
            include_suffixes = False
            phone_generator = PasswordGenerator(length=10, include_uppercase=False, include_numbers=True)
            phone = phone_generator.generate()
            print(f"Generated Phone Number: {phone}")

        elif choice == 3:
            include_email_format = True
            include_password = False
            include_phone_format = False
            include_suffixes = False
            email_generator = PasswordGenerator(length=6, include_uppercase=True, include_numbers=False)
            email = email_generator.generate()
            print(f"Generated Email Address: {email}")

        elif choice == 4:
            include_suffixes = True
            include_password = False
            include_phone_format = False
            include_email_format = False
            suffixes = []
            suffixes.append(f"{random.choice(string.ascii_lowercase)}-{random.randint(1, 99)}")
            suffixes.append(f"{random.choice(string.ascii_uppercase)}-{random.randint(1, 99)}")
            suffixes.append(f"{random.choice(string.digits)}-{random.randint(1, 99)}")
            suffixes.append(f"{random.choice(string.punctuation)}-{random.randint(1, 99)}")
            suffixes.append(f"{random.choice(string.ascii_lowercase)}-{random.randint(1, 99)}-{random.choice(string.ascii_uppercase)}-{random.randint(1, 99)}")
            suffixes.append(f"{random.choice(string.digits)}-{random.randint(1, 99)}-{random.choice(string.punctuation)}-{random.randint(1, 99)}")
            print("Generated First/Last Name Suffixes: " + str(suffixes))

        elif choice >= 6:
            print("Please choose an option between 1-4")

        if choice >= 6:
            main()

if __name__ == "__main__":
    main()

You can run this script from the terminal or command prompt and interact with it using the menu provided. The script will keep running and the menu will keep being displayed until the user closes the terminal. To exit the script, choose option 1 and then press enter.