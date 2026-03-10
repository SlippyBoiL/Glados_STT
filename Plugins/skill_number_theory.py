# DESCRIPTION: Find prime numbers up to a given number.
# --- GLADOS SKILL: skill_number_theory.py ---


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def get_prime_numbers(n):
    return [i for i in range(2, n + 1) if is_prime(i)]


def main():
    n = 50
    primes = get_prime_numbers(n)
    print(f"Primes up to {n}: {primes}")


if __name__ == "__main__":
    main()
