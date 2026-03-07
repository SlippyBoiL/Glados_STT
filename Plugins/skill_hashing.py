# DESCRIPTION: a simple Python script for hashing passwords.
# --- GLADOS SKILL: skill_hashing.py ---

#!/usr/bin/env python3

import getpass
import hashlib
import os
import time
import uuid

def generate_password(length=16):
    """Generates a random password"""
    alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(uuid choice(alphabet) for uuid in range(length))

def main():
    password = input("Enter a password or press Enter to generate a random one: ")
    if not password:
        password = generate_password()

    # Hash the password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    print("Hashed Password:", hashed_password)

    # Create a file with the hashed password
    filename = f"password_{getpass.getuser()}_{getpass.getuid()}_{time.time()}.txt"
    with open(filename, 'w') as f:
        f.write(hashed_password)

    print("Password saved to:")
    print(filename)

    # Display the password
    print("Your password is:")
    print(password)

if __name__ == "__main__":
    main()