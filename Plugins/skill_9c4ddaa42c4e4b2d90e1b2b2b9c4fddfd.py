# DESCRIPTION: A skill file for {file_path}"
# --- GLADOS SKILL: skill_9c4ddaa42c4e4b2d90e1b2b2b9c4fddfd.py ---

import hashlib
import mimetypes
import os
import pathlib
import shutil
import time

def get_similar_files(root_directory):
    similar_files = {}
    for root, dirs, files in os.walk(root_directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_hash = sha256(file_path)
            similar_files[file_hash] = [file_path]
            similar_files[f"{file_hash}_{os.path.ext(file_path)}"] = [file_hash]
    return similar_files

def remove_similar_duplicates(root_directory):
    files_to_remove = {}
    for root, dirs, files in os.walk(root_directory):
        similar_files = get_similar_files(root_directory)
        for file_hash, file_paths in similar_files.items():
            if len(file_paths) > 1:
                files_to_remove[file_hash] = file_paths
    for file_hash, file_paths in files_to_remove.items():
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed duplicate file: {file_path}")

def organize_files(root_directory):
    sorted_files = sorted(get_similar_files(root_directory), key=lambda x: x[:4])
    for file_hash in sorted_files:
        for file_hash_without_extension in [file_hash.split("_")[0]] * (len(file_hash.split("_")) > 1):
            os.makedirs(os.path.join(root_directory, file_hash_without_extension), exist_ok=True)
        for file_path in get_similar_files(root_directory)[file_hash]:
            new_file_name = "_".join(file_hash.split("_"))
            new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
            os.rename(file_path, new_file_path)

def create_backup(root_directory):
    backup_directory = root_directory + "_backup"
    os.makedirs(backup_directory, exist_ok=True)
    for root, dirs, files in os.walk(root_directory):
        for file in files:
            file_path = os.path.join(root, file)
            new_file_path = os.path.join(backup_directory, file_path)
            destination = file_path.split(os.path.sep)
            source = [new_file_path]
            destination[0] = source[0]
            source.append(new_file_path)
            shutil.move(os.path.join(root, file), *destination)
    print("Backup created")

def backup_archive(root_directory):
    extension = mimetypes.guess_extension(root_directory + ".*")
    shutil.make_archive(root_directory, 'zip', root_directory)
    new_file_name = f"{root_directory}_backup.zip"
    new_file_path = os.path.join(root_directory, new_file_name)
    os.rename(root_directory + "archive.zip", new_file_name)
    os.rename(new_file_path, new_file_name)
    print(f"Backup archive created: {new_file_path}")

def main():
    mode = input("Choose an action (1 - duplicate, 2 - organize, 3 - backup): ")
    if mode == "1":
        remove_similar_duplicates(input("Enter the directory: "))
    elif mode == "2":
        organize_files(input("Enter the directory: "))
    elif mode == "3":
        create_backup(input("Enter the directory: "))
    else:
        print("Invalid action")

if __name__ == "__main__":
    main()