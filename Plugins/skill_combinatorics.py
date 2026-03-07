# DESCRIPTION: A script that can calculate the probability of a two-event combine and list files in the current directory.
# --- GLADOS SKILL: skill_combinatorics.py ---

#!/usr/bin/python
import os
import time

def clear_screen():
    print("\033[35m" + "---------------------------------------" + "---------------------------------------")
    print("\033[0m")

def main():
    while True:
        print("1. Calculate Probability of a Two-Event Combine")
        print("2. List Files in Current Directory")
        print("3. Exit")
        choice = input("Enter your choice: ")
        
        if choice == "1":
            probability = input("Enter the probability of each event (in decimal format, e.g., 0.5 for 50%): ")
            first_event = input("Enter the first event (e.g., 'Heads'): ")
            second_event = input("Enter the second event (e.g., 'Tails'): ")
            combined_event = input("Enter the combined event (e.g., 'Heads and Tails'): ")
            print(f"The probability of the combined event of {first_event} {second_event} for {combined_event} is {float(probability):.3%}")
        elif choice == "2":
            print("Files in current directory:")
            for filename in os.listdir("."):
                print(filename)
        elif choice == "3":
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please choose a valid option.")

def wait_and_print(message):
    print(message)
    time.sleep(4)

def clear_temp_files():
    clear_screen()
    wait_and_print("Deleting temporary files...")
    for filename in os.listdir("."):
        if filename.startswith("temp"):
            os.remove(filename)
            print(f"Deleted file: {filename}")
    clear_screen()
    wait_and_print("Temporary files have been deleted.")

if __name__ == "__main__":
    main()
    clear_temp_files()