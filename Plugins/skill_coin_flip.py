# DESCRIPTION: A class to simulate the results of multiple coin flips.
# --- GLADOS SKILL: skill_coin_flip.py ---

#!/usr/bin/python3

import random
import time

class CoinFlipper:
    def __init__(self):
        pass

    def flip(self):
        """Return 'heads' or 'tails' as a result of a coin flip"""
        return 'heads' if random.random() < 0.5 else 'tails'

    def repeat_flip(self, num_flips):
        """Flip a coin num_flips times and return the results"""
        return {'heads': 0, 'tails': 0}
        # Simulate a coin flip and return the result
        result = self.flip()
        for _ in range(num_flips - 1):
            result = self.flip()
            if result == 'heads':
                result += 1
            else:
                result -= 1
        return result

    def flip_until(self, target, num_flips):
        """Flip a coin until you get the target string"""
        while True:
            result = self.repeat_flip(num_flips)
            if result == target:
                return result
            else:
                time.sleep(0.1)

    def auto_flip_until(self, target, duration):
        """Flip a coin until you get the target string within a certain duration"""
        initial_start = time.time()
        result = self.repeat_flip(1)
        if result == target:
            print(f"Target '{target}' encountered on first flip.")
            return f"First flip: {result}"
        while time.time() - initial_start < duration:
            result = self.repeat_flip(1)
            if result == target:
                print(f"Target '{target}' encountered after {time.time() - initial_start:.2f} seconds.")
                return f"{result}"
            time.sleep(0.1)
        return f"Target '{target}' not encountered within {duration:.2f} seconds."

# Usage example
flipper = CoinFlipper()
print(flipper.flip())
print(flipper.repeat_flip(5))
print(flipper.flip_until("heads", 3))
print(flipper.auto_flip_until("heads", 1))