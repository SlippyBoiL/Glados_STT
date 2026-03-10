# DESCRIPTION: Lists directories in a path sorted by size.
# --- GLADOS SKILL: skill_list_sorted_directories.py ---

import os


def list_sorted_directories(path):
    try:
        dirs = [
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d))
        ]
        return sorted(dirs, key=lambda d: os.path.getsize(os.path.join(path, d)))
    except (FileNotFoundError, OSError):
        return []


def main():
    path = "."
    dirs = list_sorted_directories(path)
    print(f"Directories in '{path}' (sorted by size):")
    for d in dirs[:15]:
        print(f"  {d}")
    if len(dirs) > 15:
        print("  ...")


if __name__ == "__main__":
    main()
