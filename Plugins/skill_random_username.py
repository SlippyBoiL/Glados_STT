# DESCRIPTION: Generates random usernames with a specified length.
# --- GLADOS SKILL: skill_random_username.py ---

# skill_random_username.py

import sys
import random
import string

def generate_username(length=8):
    """Generate a random username."""
    characters = (
        string.ascii_lowercase
        + string.ascii_uppercase
        + string.digits
        + string.punctuation
    )
    return ''.join(random.choice(characters) for _ in range(length))

def main():
    if len(sys.argv) > 1:
        length = int(sys.argv[1])
    else:
        length = 8

    username = generate_username(length)
    print(f"Generated random username: {username}")

    save_to_file = input("Would you like to save this username to a file? (y/n): ")
    if save_to_file.lower() == 'y':
        filename = input("Enter filename: ")
        with open(filename, 'w') as f:
            f.write(username)

if __name__ == '__main__':
    main()