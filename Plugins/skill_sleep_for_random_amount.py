# DESCRIPTION: Briefly sleeps for a few seconds to simulate "thinking".
# --- GLADOS SKILL: skill_sleep_for_random_amount.py ---

import random
import time


def skill_sleep_for_random_amount_in_seconds() -> None:
    # Keep it short so skills don't appear to hang forever.
    sleep_time = random.randint(3, 8)
    print(f"Pausing for {sleep_time} seconds...")
    time.sleep(sleep_time)
    print("Pause complete.")


def main() -> None:
    skill_sleep_for_random_amount_in_seconds()


if __name__ == "__main__":
    main()