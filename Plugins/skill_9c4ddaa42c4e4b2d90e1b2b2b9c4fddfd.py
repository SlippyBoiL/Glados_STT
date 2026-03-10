# DESCRIPTION: Lists files in current directory with SHA256 hash (read-only).
# --- GLADOS SKILL: skill_9c4ddaa42c4e4b2d90e1b2b2b9c4fddfd.py ---

import hashlib
import os


def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except (OSError, IOError):
        return "N/A"


def main():
    print("Files in current directory (with hash prefix):")
    for name in sorted(os.listdir("."))[:15]:
        if os.path.isfile(name):
            print(f"  {file_hash(name)}  {name}")
    if len(os.listdir(".")) > 15:
        print("  ...")


if __name__ == "__main__":
    main()
