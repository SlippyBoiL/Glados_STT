# DESCRIPTION: This script provides utility functions for calculating a file's size, checksum, and verifying the file's age.
# --- GLADOS SKILL: skill_de.py ---

import hashlib
import os
import time

def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        print(f"Error occurred while getting file size: {e}")
        return None

def calculate_checksum(file_path):
    file_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        content = f.read()
        file_hash.update(content)
    return file_hash.hexdigest()

def age_file_timestamp(file_path):
    return file_path.split('.')[-1]

def detect_data_type(file_path):
    file_extension = file_path.split('.')[-1]
    if file_extension == 'csv':
        return 'CSV'
    elif file_extension == 'txt':
        return 'Text'
    elif file_extension == 'jpg':
        return 'Image'
    else:
        return "Unknown"

def main():
    file_path = input("Please enter a file path: ")
    file_size = get_file_size(file_path)
    file_checksum = calculate_checksum(file_path)
    file_timestamp = age_file_timestamp(file_path)
    file_type = detect_data_type(file_path)

    if file_size is not None:
        print(f"File size: {file_size} bytes")
    if file_checksum:
        print(f"File checksum: {file_checksum}")
    if file_timestamp:
        print(f"File timestamp: {time.ctime(time.mktime(time.strptime(f"{file_path.split('.')[-1]}.{file_timestamp}", '%a %b %d %H:%M:%S.')"))}")
    if file_type:
        print(f"File type: {file_type}")
    else:
        print("File type: Unknown")

    wait = input("Would you like to wait for a minute? Type 'y' to wait. Type anything else to exit: ")
    if wait.lower() == 'y':
        time.sleep(60)
        print("Script exiting...")

if __name__ == "__main__":
    main()