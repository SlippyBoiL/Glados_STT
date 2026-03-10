# DESCRIPTION: This code defines functions to generate random salts and create weak passwords by hashing input strings with the provided salts.
# --- GLADOS SKILL: skill_generate_password.py ---

import hashlib
import os
import time
import uuid
import random

def generate_random_salt(length=16):
    """Generate a random salt with the given length."""
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(length))

def create_weak_password(input_string, salt):
    """Create a weak password by hashing the input string with the provided salt."""
    hashed_password = hashlib.sha256(f'{input_string}{salt}'.encode()).hexdigest()
    return hashed_password

def check_password(input_string, hashed_password, salt):
    """Check if the provided input string matches the hashed password."""
    return hashlib.sha256(f'{input_string}{salt}'.encode()).hexdigest() == hashed_password

def generate_strong_password(length=16, min_digits=1, min_uppercase=1, min_lowercase=1):
    """Generate a strong password with the given length, numbers, uppercase, and lowercase characters."""
    password = [random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(min_lowercase)]
    password += [random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(min_uppercase)]
    password += [random.choice('0123456789') for _ in range(min_digits)]
    for _ in range(length - min_lowercase - min_uppercase - min_digits):
        password.append(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'))
    random.shuffle(password)
    return ''.join(password)

def main():
    if len(sys.argv) < 2:
        print("Usage:", sys.argv[0], "[-s <salt>]", "[-p <password>]", "[-f <filename>]")
    else:
        action = sys.argv[1].lower()
        input_string = None
        password = None
        filename = None
        salt = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '-s' and i < len(sys.argv) - 2:
                salt = sys.argv[i + 2]
            elif arg == '-p' and i < len(sys.argv) - 2:
                password = generate_strong_password()
            elif arg == '-f' and i < len(sys.argv) - 2:
                filename = sys.argv[i + 2]
            else:
                if input_string is None:
                    input_string = arg
                else:
                    print("Too many input values")
                    return
        if action == 'check':
            if input_string and salt:
                print(check_password(input_string, password, salt))
            else:
                print("Either input_string or salt must be provided")
                return
        elif action == 'generate':
            if input_string and salt:
                create_weak_password(input_string, salt)
            else:
                print("Either input_string or salt must be provided.")
                return
        elif action == 'generate_password':
            if password:
                print(password)
            else:
                print("password argument must be provided")
                return
        elif action in ['weak', 'weak_password']:
            if len(password):
                print(create_weak_password(input_string, salt))
            else:
                print("password argument must be provided")
                return
        elif action in ['strong', 'strong_password']:
            if len(password):
                print(password)
            else:
                print("password argument must be provided")
                return
        elif action == 'help':
            print("Usage:", sys.argv[0], "[-s <salt>]", "[-p <password>]", "[-f <filename>]")
        else:
            print("Invalid action:", action)
    if not password:
        print("Please use one of the following actions:")
        print("create_weak_password", "generate", "generate_password", "check", "generate_password", "weak")

if __name__ == '__main__':
    import sys
    main()