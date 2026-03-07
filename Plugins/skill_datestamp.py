# DESCRIPTION: A script that generates datestamps in a loop, writing them to separate text files with a delay of 1 second between each generation.
# --- GLADOS SKILL: skill_datestamp.py ---

import os
import time

def skill_datestamp():
    for i in range(5):
        for j in range(3):
            datestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            with open(f'datestamp_{i}_{j}.txt', 'w') as f:
                f.write(datestamp)
            time.sleep(1)

def main():
    print("Date Stamp Generator")
    print("---------------------")
    skill_counter = 0
    while True:
        skill_datestamp()
        print(f"Written datestamp_{skill_counter}_{0}.txt")
        print(f"Written datestamp_{skill_counter}_{1}.txt")
        print(f"Written datestamp_{skill_counter}_{2}.txt")
        time.sleep(2)
        skill_counter += 1

if __name__ == "__main__":
    main()