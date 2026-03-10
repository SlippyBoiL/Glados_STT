# DESCRIPTION: Script to generate a checksum for a given file.`
# --- GLADOS SKILL: skill_generate_checksum.py ---

#!/usr/bin/env python3

import hashlib
import os
import uuid
import datetime
import random
import sys

def generate_checksum(filename):
    """
    Generate a checksum for a given file.
    """
    try:
        with open(filename, 'rb') as file:
            data = file.read()
            checksum = hashlib.sha256(data).hexdigest()
        return checksum
    except FileNotFoundError:
        print(f"File {filename} does not exist.")
        return None

def check_file_size(filename, size):
    with open(filename, 'rb') as file:
        file-size = file.tell()
    return file-size == size

def find_files_in_directory(directory):
    """
    Find all files in a given directory.
    """
    return [os.path.join(directory, file) for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]

def get_os_info():
    """
    Get system information.
    """
    os_info = {}
    os_info["platform"] = sys.platform
    os_info["python"] = sys.version
    os_info["cpu_count"] = os.cpu_count()
    for core in os.cpu_count(logical=False):
        os_info[f"CPU_core_{core}"] = os.cpu_freq(logical=False).max / 1000
    os_info["memory"] = os.memory_info().rss / 1024 / 1024 / 1024
    return os_info

def print_os_info(os_info):
    """
    Print system information in a human-readable format.
    """
    for key, value in os_info.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

def main():
    if len(sys.argv) == 2:
        filename = sys.argv[1]
        checksum = generate_checksum(filename)
        print(checksum or "No checksum found.")
    elif len(sys.argv) > 2:
        directory = sys.argv[1]
        files = find_files_in_directory(directory)
        if files:
            print("Files in directory:")
            for file in files:
                print(file)
        else:
            print("Directory is empty.")
    else:
        os_info = get_os_info()
        print("System Information:")
        print_os_info(os_info)

if __name__ == "__main__":
    main()