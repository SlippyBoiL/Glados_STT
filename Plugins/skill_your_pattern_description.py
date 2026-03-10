# DESCRIPTION: The script renames files in the specified folder based on a given pattern.
# --- GLADOS SKILL: skill_your_pattern_description.py ---

import os
import json
import re
from datetime import datetime, timedelta

def remove_comments_from_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        modified_lines = []
        for line in lines:
            line = re.sub(r'\#.*', '', line)
            modified_lines.append(line)
    with open(file_path, 'w') as file:
        file.writelines(modified_lines)

def rename_files_in_folder(folder_path, prefix, suffix, pattern):
    files = os.listdir(folder_path)
    for file in files:
        if re.search(pattern, file):
            new_name = f"{prefix}_{file}{suffix}"
            os.rename(os.path.join(folder_path, file), os.path.join(folder_path, new_name))

def convert_json_date_to_datetime(json_path):
    with open(json_path, 'r') as file:
        data = json.load(file)
    for key, value in data.items():
        if isinstance(value, str) and len(value) == 10:
            data[key] = datetime.strptime(value, "%Y-%m-%d")
    with open(json_path, 'w') as file:
        json.dump(data, file)

def get_number_of_files_in_folder(folder_path):
    return len(os.listdir(folder_path))

def create_timestamp_file(folder_path, filename):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(folder_path, f"{filename}_{timestamp}.txt")
    with open(file_path, 'w') as file:
        file.write(timestamp)
    return file_path

def check_for_updates(skill_path, current_version, latest_update):
    with open(skill_path, 'r') as file:
        file_data = file.read()
    if file_data != latest_update:
        print("Update available. Please install the latest version.")
        return True
    else:
        return False

def skills_folder_watcher(folder_path):
    return os.path.isdir(folder_path)

if __name__ == "__main__":
    usage = """
    usage: python -m skills
    --folder <folder_path>
    --prefix <prefix>
    --suffix <suffix>
    --pattern <pattern>
    --json <json_path>
    --number <number>
    --file <filename>
    --current_version <current_version>
    --latest_update <latest_update>
    """

    import argparse
    parser = argparse.ArgumentParser(description="Skills folder watcher.")
    required_arguments = ["folder"]
    optional_arguments = []

    for arg in required_arguments:
        parser.add_argument(f"--{arg}", help=arg, required=True)

    for arg in optional_arguments:
        parser.add_argument(f"--{arg}", help=arg, required=False)

    args = parser.parse_args()

    if len(args) != len(required_arguments):
        print("The number of arguments provided is not correct.")
        print(usage)
        exit(1)

    folder_path = args["--folder"]
    prefix = args["--prefix"]
    suffix = args["--suffix"]
    pattern = args["--pattern"]
    json_path = args["--json"]
    number = args["--number"]
    filename = args["--file"]
    current_version = args["--current_version"]
    latest_update = args["--latest_update"]

    if args["--skills_folder_watcher"]:
        print(f"The {folder_path} is a folder.")
    if folder_path.isnumeric() != True:
        print(f"The {folder_path} is not a folder.")
    if folder_path.isalpha() != True:
        print(f"The {folder_path} is not a folder.")
    if os.path.isdir(folder_path) == False:
        print(f"The {folder_path} is not a folder.")
    if number is not None and number < 1:
        print("Number must be a positive integer.")
    if filename is not None and len(filename) < 1:
        print("Filename must be at least 1 character.")
    if current_version is None and latest_update is None:
        print("Current version and latest update are both required.")
        print(usage)
        exit(1)

    if current_version == latest_update and folder_path is None:
        print(f"The {folder_path} does not exist.")
    if current_version == latest_update and (json_path is False or json_path is None):
        print(f"The {folder_path} does not exist.")
    if folder_path is True or folder_path is True or folder_path is None:
        print(f"The {folder_path} path is invalid.")
    if current_version is None and latest_update is None:
        print("Current version and latest update are both required.")
        print(usage)
        exit(1)