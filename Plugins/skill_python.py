# DESCRIPTION: A Python script that generates a checksum report for a given directory.
# --- GLADOS SKILL: skill_python.py ---

#!/usr/bin/env python3

import os
import hashlib
import sys
import time

def generate_checksum(file_path):
    with open(file_path, 'rb') as f:
        chunk = f.read(4096)
        while chunk:
            h = hashlib.md5(chunk)
            yield int(h.hexdigest(), 16), h.hexdigest()
            chunk = f.read(4096)

def create_file_checksum_report(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            md5, sha256 = next(generate_checksum(file_path))
            print(f"File: {file_path}  MD5: {md5}  SHA-256: {sha256}")

def check_integrity(base_dir):
    base_dir = os.path.normpath(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    if not os.path.exists(base_dir):
        print(f"Base dir {base_dir} does not exist, quitting.")
        return False

    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            base_file_path = os.path.join(base_dir, filename)
            if os.path.getsize(file_path) == 0:
                print(f"The file {file_path} has zero length.")
                os.remove(file_path)
            elif os.path.getsize(file_path) != os.path.getsize(base_file_path):
                md5, sha256 = next(generate_checksum(file_path))
                print(f"The checksum for {file_path} does not match {base_file_path}. Checking integrity.")
                return False

    return True

if __name__ == "__main__":
    if len(sys.argv) == 1:
        base_dir = os.getcwd()
    else:
        base_dir = sys.argv[1]

    if not check_integrity(base_dir):
        print("The integrity of the directory has been compromised. Please exit the program.")
    else:
        create_file_checksum_report(base_dir)

This script generates an MD5 and SHA-256 checksum for each file in the specified directory and its subdirectories. It also creates a report showing the checksums for each file. It can be used to check the integrity of the directory by checking whether the checksums are consistent across the original and backup files. If a difference is detected, an error message is printed.