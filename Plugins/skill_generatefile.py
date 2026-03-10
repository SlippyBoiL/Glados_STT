# DESCRIPTION: A script that generates and touches a file with a randomly generated filename.
# --- GLADOS SKILL: skill_generatefile.py ---

import uuid
import time
import os

def generate_random_file_path(filename):
    return f"temp_{uuid.uuid4()}.{filename}"

def touch_file(filename):
    with open(filename, "w") as f:
        pass

def main():
    while True:
        file_name = input("Enter filename to generate and touch: ")
        file_path = generate_random_file_path(file_name)
        touch_file(file_path)
        print(f"File {file_path} generated and touched successfully!")

        response = input("Would you like to generate and touch another file? (y/n): ")
        if response.lower() != "y":
            break

if __name__ == "__main__":
    main()
    while True:
        time.sleep(60)


You can run this script in your terminal, enter the name of the file you want to generate and touch, and then enter 'y' to generate and touch another file, or 'n' otherwise, the script will terminate. The script will then sleep for 60 seconds and repeat this process. It will generate a unique filename and a new file with that name, touching it for you.