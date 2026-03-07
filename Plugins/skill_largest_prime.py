# DESCRIPTION: This module provides a function for finding the largest prime factor of a given number.
# --- GLADOS SKILL: skill_largest_prime.py ---

import time
import sys
import random
import os

def skill_largest_prime(n):
    if n < 2:
        return None
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return i
    return n

def skill_get_prime_factorization(n):
    factors = []
    i = 2
    while i * i <= n:
        if n % i:
            i += 1
        else:
            n //= i
            factors.append(i)
    if n > 1:
        factors.append(n)
    return factors

def skill_get_n_to_n_prime_factors(n, num_factors):
    prime_factors = []
    for i in range(2, n + 1):
        if skill_is_prime(i) and len(prime_factors) < num_factors:
            prime_factors.append(i)
    return prime_factors

def skill_is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def skill_largest_prime_divisor(n):
    return skill_largest_prime(n)

def main():
    if len(sys.argv) != 2:
        print("Usage: python largest_prime.py <number>")
        sys.exit(1)
    
    number = int(sys.argv[1])
    prime_factors = skill_get_n_to_n_prime_factors(number, 5)
    largest_prime = max(prime_factors)
    return "{} is not the largest prime".format(number) if largest_prime == number else f"{number} is the largest prime ({largest_prime})"

if __name__ == "__main__":
    print("\nLargestPrime Script (v1.0)")
    start_time = time.time()
    print(main())
    end_time = time.time()
    print(f"Script duration: {end_time - start_time} seconds")
    print("Memory usage: {:.2f} Mb".format(os.path.getsize('/proc/self/statm') / 1024.0))