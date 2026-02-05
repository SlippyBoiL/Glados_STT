# DESCRIPTION: Flips a coin.
# --- GLADOS SKILL: skill_coinflip.py ---

import random

def flip():
    return "Heads." if random.choice([True, False]) else "Tails."

if __name__ == "__main__":
    print(flip())