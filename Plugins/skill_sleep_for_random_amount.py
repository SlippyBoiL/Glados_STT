# DESCRIPTION: This skill causes the program to pause for a random amount of time between 30 seconds to 3 minutes.
# --- GLADOS SKILL: skill_sleep_for_random_amount.py ---

import random
import time
from datetime import datetime

def skill_sleep_for_random_amount_in_seconds():
    sleep_range = [30, 60, 90, 120, 180]
    sleep_time = random.choice(sleep_range) * 60
    print(f"Sleeping for {sleep_time} seconds...")
    time.sleep(sleep_time)

skill_sleep_for_random_amount_in_seconds()