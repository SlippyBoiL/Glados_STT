# DESCRIPTION: Retrieves and returns user information from the /etc/passwd file.
# --- GLADOS SKILL: skill_unknown.py ---

import datetime

def get_user_info():
    try:
        with open('/etc/passwd', 'r') as file:
            for line in file.readlines():
                line = line.strip()
                if len(line.split(':')[0]) > 0:
                    return {
                        'username': line.split(':')[0],
                        'hostname': line.split(':')[1],
                        'uid': int(line.split(':')[2]),
                        'gid': int(line.split(':')[3]),
                        'gecos': line.split(':')[4],
                        'home_directory': line.split(':')[5],
                        'shell': line.split(':')[6]
                    }
    except FileNotFoundError:
        print("Unable to read /etc/passwd")
    except Exception:
        print("An unknown error occurred")
    return None

def main():
    print("Python Version Checker")
    print("------------------------")
    print(f"Python version: {python_version_checker()}")

python_version_checker = lambda: platform.python_version()

if __name__ == "__main__":
    main()


This script provides a simple program that checks and prints the currently active version of Python that is being used.