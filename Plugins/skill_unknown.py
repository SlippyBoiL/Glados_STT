# DESCRIPTION: The file '{name}' last modified on {datetime.date.today()}")
# --- GLADOS SKILL: skill_unknown.py ---

import hashlib
import os
import datetime
import argparse

class FileChecker:
    def __init__(self):
        pass

    def file_last_modification(self):
        def get_size(file_path):
            try:
                return os.path.getsize(file_path)
            except OSError:
                return None

        for root, dirs, files in os.walk('.'):
            for file in files:
                file_path = os.path.join(root, file)

                size = get_size(file_path)

                if size is not None:
                    print(f"File: {file_path}, Last Modified: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def file_md5hash(self):
        def get_md5_hash(file_path):
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        for root, dirs, files in os.walk('.'):
            for file in files:
                file_path = os.path.join(root, file)

                print(f"File: {file_path} - MD5 Hash: {get_md5_hash(file_path)}")


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--last_mod":
            file_checker.file_last_modification()

        elif sys.argv[1] == "--md5":
            file_checker.file_md5hash()

        else:
            print("Invalid command line argument. Please use --last_mod or --md5.")
            return

    else:
        parser = argparse.ArgumentParser(description="File Checker Tool")
        parser.add_argument("--last_mod")
        parser.add_argument("--md5")
        args = parser.parse_args()

        if args.last_mod:
            file_checker.file_last_modification()

        elif args.md5:
            file_checker.file_md5hash()

        else:
            print("Please provide a valid command line argument (-l or -m).")
            return


if __name__ == "__main__":
    sys.argv = sys.argv[1:]  # ignore the __main__ module
    main()