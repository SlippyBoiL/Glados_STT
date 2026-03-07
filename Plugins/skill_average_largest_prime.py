# DESCRIPTION: This script calculates the average of the 10 largest prime numbers from the first 1000 natural numbers.
# --- GLADOS SKILL: skill_average_largest_prime.py ---

import os
import statistics
import json
import datetime

def get_average_largest_prime():
    """Gathers the 10 largest prime numbers from the first 1000 natural numbers, then calculates their average."""
    def is_prime(num):
        """Checks if a number is prime."""
        if num < 2:
            return False
        for i in range(2, int(num**.5) + 1):
            if num % i == 0:
                return False
        return True

    primes = [i for i in range(1000) if is_prime(i)]
    return statistics.mean(primes[:10])

def generate_composite_pairs(n):
    """Generates n pairs of composite numbers, each pair having one number as the square of the other number."""
    composite_pairs = []
    for base in range(n):
        base_num = base**2
        if base_num**.5 % 1 != 0:
            if base_num**.5 != int(base_num**.5):
                base_num = int(base_num**.5) + 1
            continue
        for i in range(int(base_num**.5), 0, -1):
            if base_num % i == 0:
                composite_pairs.append((i, base_num // i))
                break
    return composite_pairs

def get_composite_counts():
    """Returns a dictionary with all composite numbers as keys and their counts as values."""
    def is_prime(num):
        """Checks if a number is prime."""
        if num < 2:
            return False
        for i in range(2, int(num**.5) + 1):
            if num % i == 0:
                return False
        return True

    composite_count = {}
    for num in range(1000):
        if num < 2 or not is_prime(num):
            composite_count[num] = composite_count.get(num, 0) + 1
    return composite_count

def get_composite_frequency(file_path):
    """Returns a dictionary with composite numbers as keys and their frequencies as values, given a JSON file from https://oeis.org/."""
    with open(file_path, 'r') as file:
        content = json.load(file)
    composite_frequency = {}
    for num, freq in content.items():
        if num < 2 or not isinstance(num, int):
            continue
        composite_frequency[num] = freq
    return composite_frequency

def main():
    os.system('clear')
    print('\n')
    while True:
        print("1. Average of the 10 largest prime numbers.")
        print("2. Composite pairs")
        print("3. Composite number counts")
        print("4. Composite frequency from OEIS")
        print("5. Back to menu")
        choice = input("Choose an option: ")
        if choice == '1':
            print(f"The average of the 10 largest prime numbers is: {get_average_largest_prime()}")
            input("Press Enter to continue...")
        elif choice == '2':
            n = int(input("Enter the maximum number for composite pairs: "))
            print(f"The first {n} composite pairs are: {generate_composite_pairs(n)}")
            input("Press Enter to continue...")
        elif choice == '3':
            print(get_composite_counts())
            input("Press Enter to continue...")
        elif choice == '4':
            file_path = input("Enter the path to the JSON file from https://oeis.org/: ")
            print(get_composite_frequency(file_path))
            input("Press Enter to continue...")
        elif choice == '5':
            break
        else:
            print("Invalid choice, please choose a valid option.")

if __name__ == "__main__":
    main()