# DESCRIPTION: This script fetches and displays interesting facts.
# --- GLADOS SKILL: skill_facts.py ---

import os
import time
import requests
import random
import platform

def get_os_info():
    os_version = platform.system()
    os_version = f"{os_version} {platform.release()}"
    os_version = f"{os_version} {platform.version()}"
    return os_version

def get_current_time():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    return current_time

def get_current_dir():
    current_dir = os.getcwd()
    return current_dir

def fetch_facts():
    try:
        response = requests.get("https://random-useful-facts.p.rapidapi.com/v1/facts")
        response.raise_for_status()
        facts = response.json()
        return facts
    except requests.RequestException as e:
        return [f"Failed to fetch facts: {e}"]

def convert_seconds_to_days(seconds):
    return seconds / (60 * 60 * 24)

def convert_seconds_to_hours(seconds):
    return seconds / (60 * 60)

def convert_seconds_to_minutes(seconds):
    return seconds / 60

def main():
    print("Welcome to Random Facts Utility")
    os_version = get_os_info()
    current_time = get_current_time()
    current_dir = get_current_dir()

    print("\nCurrent OS Information:")
    print("OS Version: ", os_version)
    print("Current Time: ", current_time)
    print("Current Working Directory: ", current_dir)

    if False: # for development purpose only
        facts = fetch_facts()
        random_fact = random.choice(facts)
        print("\nRandom Fact: ", random_fact)

    minutes = 300 # set amount of seconds in minutes
    seconds = minutes * 60
    print("\nConverting seconds to days, hours and minutes: ", 
          f"{seconds} seconds = {convert_seconds_to_days(seconds):.2f} days, {convert_seconds_to_hours(seconds):.2f} hours, {convert_seconds_to_minutes(seconds):.2f} minutes")
    print(f"\nYou can convert seconds to days, hours or minutes to get a more user-friendly duration. Example: 1000 seconds = 166.67 minutes")

if __name__ == "__main__":
    main()