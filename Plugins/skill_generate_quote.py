# DESCRIPTION: This script generates a random quote along with its author.
# --- GLADOS SKILL: skill_generate_quote.py ---

import datetime
import random
import secrets

def generate_random_quote():
    authors = ["Bertolt Brecht", "Aristotle", "William Shakespeare", "George Orwell", "Mick Jagger"]
    quotes = [
        "The biggest mistake you can make is not trying",
        "The only person you are destined to become is the person you decide to be",
        "The greatest glory in living lies not in never falling, but in rising every time we fall",
        "The most important thing in life is to learn how to give out love, and let it come in",
        "Life is 10% what happens to you and 90% how you react to it"
    ]
    return f'"{random.choice(quotes)}" - {random.choice(authors)}'

def generate_password(length):
    characters = "abcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(characters) for _ in range(length))

def generate_unique_id(length):
    return secrets.token_urlsafe(length)

def main():
    while True:
        print(generate_random_quote())
        print(f"Password: {generate_password(12)}")
        print(f"Unique ID: {generate_unique_id(16)}")
        print("Sleeping for 10 seconds...")
        import time
        time.sleep(10)

if __name__ == "__main__":
    main()