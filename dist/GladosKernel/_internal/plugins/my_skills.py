# GLADOS PERMANENT SKILLS


# --- NEW SKILL ADDED Sat Jan 31 19:26:58 2026 ---
def is_prime(n):
    """Check if a number is prime. Returns True if prime, False otherwise."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    # Check odd divisors up to sqrt(n) for efficiency
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True

def find_primes(count):
    """Find the first 'count' prime numbers."""
    primes = []
    num = 2
    while len(primes) < count:
        if is_prime(num):
            primes.append(num)
        num += 1
    return primes

# Main execution
prime_list = find_primes(20)
print("First 20 prime numbers:", prime_list)
# Output: First 20 prime numbers: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
