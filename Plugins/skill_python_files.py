# DESCRIPTION: Generates a stats report of the most used files in a given directory.
# --- GLADOS SKILL: skill_python_files.py ---

import datetime
import os

def get_creation_date(path):
    return datetime.datetime.fromtimestamp(os.path.getctime(path))

def get_most_used_files(path="."):
    total_size = 0
    most_used = {}
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
                most_used[filepath] = most_used.get(filepath, 0) + 1
            except PermissionError:
                pass
    sorted_files = sorted(most_used.items(), key=lambda x: x[1], reverse=True)
    return sorted_files

def get_file_date(path="."):
    while True:
        current_date = get_creation_date(path) or get_creation_date(os.getcwd())
        print(f"Files created on: {current_date}")
        for file in path.split(os.sep)[1:]:
            path_to_file = os.path.join(path.split(os.sep)[0], file)
            if get_creation_date(path_to_file):
                continue
            print(f"  {os.path.join(path_to_file)}")
        if not any(get_creation_date(path) for path in [os.path.join(path.split(os.sep)[0], file) for file in path.split(os.sep)[1:]]):
            break

def main():
    files = get_most_used_files()
    while True:
        user_choice = input("1. Get file creation dates\n2. Get most used files\n3. Exit: ")
        if user_choice == "1":
            get_file_date()
        elif user_choice == "2":
            for file_path, count in files:
                print(f"{file_path} : {count} times")
        elif user_choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()