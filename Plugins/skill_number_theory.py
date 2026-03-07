# DESCRIPTION: Program to find and print prime numbers up to a given number.`
# --- GLADOS SKILL: skill_number_theory.py ---

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def get_prime_numbers(n):
    return [i for i in range(2, n+1) if is_prime(i)]

def sort_and_print_prime_numbers(n):
    primes = get_prime_numbers(n)
    print("Prime numbers up to", n, ":")
    print(sorted(primes))

def menu():
    while True:
        print("\nPrime number finder menu:")
        print("1. Find prime numbers within a range")
        print("2. Quit")
        choice = input("Choose an option: ")
        if choice == "1":
            n = int(input("Enter a number: "))
            sort_and_print_prime_numbers(n)
        elif choice == "2":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

menu()