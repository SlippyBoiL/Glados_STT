# DESCRIPTION: This script generates a random string of alphabetic characters of varying length.
# --- GLADOS SKILL: skill_generate_alphapart.py ---

import datetime
import random
import time

def generate_alphapart():
    letters = 'abcdefghijklmnopqrstuvwxyz'
    characters = ''
    for _ in range(random.randint(1, 10)):
        characters += random.choice(letters)
    return characters

def generate_alphacomplete():
    letters = 'abcdefghijklmnopqrstuvwxyz'
    complete_string = ''
    for letter in letters:
        complete_string += letter
    return complete_string

def random_prime(min_value=100):
    max_value = 1000000
    while True:
        value = random.randint(min_value, max_value)
        if is_prime(value):
            return value

def is_prime(n):
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    max_divisor = int(n**0.5) + 1
    for d in range(6, max_divisor, 6):
        if n % d == 0 or n % (d + 2) == 0:
            return False
    return True

def main():
    current_time = datetime.datetime.now()
    end_time = current_time + datetime.timedelta(seconds=30)
    while current_time < end_time:
        print(f"Randomly generating random prime and complete alphabet between {current_time} and {end_time}:")
        print(f"Prime: {random_prime()}")
        print(f"Alphabet: {generate_alphapart()}")
        print(f"Complete Alphabet: {generate_alphacomplete()}")
        print ""
        time.sleep(1)
        current_time = datetime.datetime.now()

if __name__ == "__main__":
    main()

  
This unique Python script will run indefinitely until manually stopped, generating random prime numbers, random complete alphabet strings, and random partial alphabet strings each second, printing them to the console, while also displaying a countdown from 30 seconds to the start of the script's execution.