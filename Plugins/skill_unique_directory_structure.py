# DESCRIPTION: A Python script that creates a customizable unique directory structure using a timestamp, ideal for version control or organizational purposes.
# --- GLADOS SKILL: skill_unique_directory_structure.py ---

# skill_unique_directory_structure.py

import os
import datetime

def create_unique_directory_structure(directory):
    """
    Creates a unique directory structure with a timestamp in the format YYYYMMDD_HHMMSS.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(directory, exist_ok=True)
    for i in range(5):
        os.makedirs(os.path.join(directory, f"level_{i}"), exist_ok=True)
        for j in range(2):
            os.makedirs(os.path.join(directory, f"level_{i}", f"feature_{j}"), exist_ok=True)

def list_directory_structure(directory):
    """
    Lists the directory structure with timestamps in the format YYYYMMDD_HHMMSS.
    """
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            target_dir = os.path.join(root, dir)
            print(f"{root}\\{dir} - {target_dir}")
            for root2, dirs2, files2 in os.walk(target_dir):
                for dir2 in dirs2:
                    target_dir2 = os.path.join(root2, dir2)
                    print(f"    {root2}\\{dir2} - {target_dir2}")

def main():
    directory = os.getcwd()
    print(f"Current directory: {directory}")
    print("\nDirectory Structure:")
    create_unique_directory_structure(directory)
    print("\nUpdated Directory Structure:")
    list_directory_structure(directory)

if __name__ == "__main__":
    main()