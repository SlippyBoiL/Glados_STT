# DESCRIPTION: Prints OS info, time, and an interesting fact.
# --- GLADOS SKILL: skill_facts.py ---

import os
import time
import platform


FACTS = [
    "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still edible.",
    "Octopuses have three hearts and blue blood.",
    "A group of flamingos is called a 'flamboyance'.",
    "Bananas are berries; strawberries are not.",
    "The shortest war in history was between Britain and Zanzibar in 1896; Zanzibar surrendered after 38 minutes.",
]


def main():
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"CWD: {os.getcwd()}")
    import random
    print(f"Fact: {random.choice(FACTS)}")


if __name__ == "__main__":
    main()
