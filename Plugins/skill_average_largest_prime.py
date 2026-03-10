# DESCRIPTION: Average of the 10 largest primes below 1000.
# --- GLADOS SKILL: skill_average_largest_prime.py ---

import statistics


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def get_average_largest_prime(limit=1000, count=10):
    primes = [i for i in range(2, limit) if is_prime(i)]
    largest = primes[-count:] if len(primes) >= count else primes
    return statistics.mean(largest) if largest else 0


def main():
    avg = get_average_largest_prime()
    print(f"Average of the 10 largest primes below 1000: {avg}")


if __name__ == "__main__":
    main()
