# DESCRIPTION: Reports most-accessed files in current directory (by walk count).
# --- GLADOS SKILL: skill_python_files.py ---

import os


def get_most_used_files(path=".", top=10):
    count_by_path = {}
    for dirpath, _dirs, filenames in os.walk(path):
        for name in filenames:
            fp = os.path.join(dirpath, name)
            try:
                count_by_path[fp] = count_by_path.get(fp, 0) + 1
            except (OSError, PermissionError):
                pass
    return sorted(count_by_path.items(), key=lambda x: -x[1])[:top]


def main():
    print("Most used files (by path count):")
    for path, count in get_most_used_files("."):
        print(f"  {path}: {count}")


if __name__ == "__main__":
    main()
