# DESCRIPTION: A Python script that calculates the size of a directory.
# --- GLADOS SKILL: skill_unique_directory_structure_sizer.py ---

# skill_unique_directory_structure_sizer.py

import os

def size_directory(path):
    """
    Calculates the size of the given directory.
    
    Args:
    path (str): The path to the directory.
    
    Returns:
    int: The size of the directory in bytes.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            fp = os.path.join(dirpath, file)
            total_size += os.path.getsize(fp)
    return total_size

def main():
    # Example usage:
    dir_path = os.path.join(os.getcwd(), "example_directory")
    if os.path.exists(dir_path):
        print(f"Size of {dir_path}: {size_directory(dir_path)} bytes")
    else:
        print(f"{dir_path} does not exist")

main()