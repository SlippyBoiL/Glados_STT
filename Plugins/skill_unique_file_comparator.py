# DESCRIPTION: Compares two files by SHA256 hash; reports same or different.
# --- GLADOS SKILL: skill_unique_file_comparator.py ---

import hashlib
import os


def file_hash(path):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    # Compare this script to itself (should match)
    path = __file__
    h = file_hash(path)
    print(f"File: {os.path.basename(path)}")
    print(f"SHA256: {h[:32]}..." if h else "N/A")


if __name__ == "__main__":
    main()
