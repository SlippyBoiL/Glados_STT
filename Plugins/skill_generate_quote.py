# DESCRIPTION: Generates a random quote along with its author.
# --- GLADOS SKILL: skill_generate_quote.py ---

import random


def generate_random_quote():
    authors = ["Bertolt Brecht", "Aristotle", "William Shakespeare", "George Orwell", "Mick Jagger"]
    quotes = [
        "The biggest mistake you can make is not trying",
        "The only person you are destined to become is the person you decide to be",
        "The greatest glory in living lies not in never falling, but in rising every time we fall",
        "The most important thing in life is to learn how to give out love, and let it come in",
        "Life is 10% what happens to you and 90% how you react to it",
    ]
    return f'"{random.choice(quotes)}" — {random.choice(authors)}'


def main():
    print(generate_random_quote())


if __name__ == "__main__":
    main()
