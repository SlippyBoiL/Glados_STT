# DESCRIPTION: This function generates a random configuration with a random username, email, and system details.
# --- GLADOS SKILL: skill_generate_random_config.py ---

import time
import random
import os
import platform

def generate_random_config():
    config = {
        'username': chr(random.randint(97, 122)),
        'email': random.choice(['user1@email.com', 'user2@email.com', 'user3@email.com'].split(',')),
        'random_number': random.randint(1, 100),
        'random_string': ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(16)),
        'operating_system': platform.system(),
        'os_version': platform.release() if platform.system() == 'Linux' else f"{platform.system()} {platform.version()}"
    }
    return config

def generate_report(config):
    report = {
        'username': config.get('username', 'Unknown'),
        'email': config.get('email', 'Unknown'),
        'random_number': config.get('random_number', 'Unknown'),
        'random_string': config.get('random_string', 'Unknown'),
        'operating_system': config.get('operating_system', 'Unknown'),
        'os_version': config.get('os_version', 'Unknown'),
        'generate_date': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return report

def create_temporary_file():
    filename = f"temp_{int(time.time())}.txt"
    with open(filename, 'w') as f:
        f.write(str(random.randint(1, 100)))
    return filename

def list_files_by_size(directory):
    sizes = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path):
            sizes.append((item, os.path.getsize(item_path)))
        elif os.path.isdir(item_path):
            sizes.extend(list_files_by_size(item_path))
    return sizes

def create_log_file():
    with open('app.log', 'w') as f:
        f.write("Application started. Current date and time: " + time.strftime("%Y-%m-%d %H:%M:%S"))

def remove_temporary_file(filename):
    if os.path.exists(filename):
        os.remove(filename)

def main():
    config = generate_random_config()
    report = generate_report(config)
    print(f"Username: {config.get('username', 'Unknown')}")
    print(f"Email: {config.get('email', 'Unknown')}")
    print(f"Random number: {config.get('random_number', 'Unknown')}")
    print(f"Random string: {config.get('random_string', 'Unknown')}")
    print(f"Operating system: {config.get('operating_system', 'Unknown')}")
    print(f"OS version: {config.get('os_version', 'Unknown')}")
    print(report)
    filename = create_temporary_file()
    print(f"Temporary file created: {filename}")
    files_by_size = list_files_by_size('/', reverse=True)
    print("\nFiles sorted by size (in descending order): ")
    for filename, filesize in files_by_size:
        print(f"{filename}: {filesize}")
    create_log_file()
    print(f"Log file created: app.log")
    remove_temporary_file(filename)

if __name__ == "__main__":
    main()