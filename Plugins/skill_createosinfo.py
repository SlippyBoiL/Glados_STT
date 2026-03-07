# DESCRIPTION: A Python script that retrieves and stores information about the operating system, including the OS name, release, kernel, architecture, and processor details.
# --- GLADOS SKILL: skill_createosinfo.py ---

import os
import time
import shutil
import hashlib
import secrets
import socket
import psutil
import datetime

def get_current_osinfo():
    os_info = {
        'OS': os.name,
        'Release': os.version().split(),  # returns a tuple, e.g., ('10', '10', '19041.1118')
        'Kernel': psutil.current_platform(),
        'Machine': os.arch(),
        'Processor': f"{psutil.cpu_count()} (CPU(s) found)" + f'\n' + str(psutil.cpu_freq().current * 1000 / 1e6) + ' MHz'
    }
    return os_info

def get_system_info():
    system_info = {
        'Hostname': socket.gethostname(),
        'Domain': socket.getfqdn(),
        'IP Address': socket.gethostbyname(socket.gethostname()),
        'Process Count': psutil.cpu_count(),  # Returns the number of CPUs
        'Memory Usage': f"{psutil.virtual_memory().used / (1024 * 1024)} MB / {psutil.virtual_memory().total / (1024 * 1024)} MB Memory"
    }
    return system_info

def generate_random_password(phrase_length=10):
    letters = [
        str(x) for x in range(10)  # 0-9
    ]
    symbols = [
        '@', '#', '%', '^', '&', '*', '-', '_', '+', '=',
        '~', '!', '$', '@', '#', '%', '^', '&', '*', '-', '_',
        '+', '=', '~', '!', '$'
    ]
    numbers = [
        str(x) for x in range(10)  # 0-9
    ]
    chars = [chr(x) for x in [(i % 3 * 65) + (i // 3 % 2 * 33) + (i // 3 // 2 * 12) + 32 for i in range(phrase_length)] + letter_names[1:] + number_names + symbols[1:] + digit_names
    result_string = ''.join(secrets.choice(letters + numbers + chars + [chr(x) for x in [[i % 33] for i in range(phrase_length)]]))
    return ''.join(random.choice(letters + symbols) for _ in range(phrase_length))

def generate_token(salt):
    hashed_bytes = hashlib.sha256(str.encode(salt))
    return hashed_bytes.hexdigest()

def main():
    try:
        os_info = get_current_osinfo()
        print("\nCURRENT SYSTEM INFORMATION:")
        for key, value in os_info.items():
            print(key + ": " + str(value))
        
        system_info = get_system_info()
        print("\nCURRENT SYSTEM DETAILS FOR " + socket.gethostname() + ":")
        for key, value in system_info.items():
            print(key + ": " + str(value))
        
        hashed = secrets.token_hex(32)
        print("\nA RANDOM, SECURE TOKEN:")
        print(hashed)
        
        random_password = generate_random_password()
        print("\nA SECURELY GAINED PASSWORD FOR YOU:")
        print(random_password)
        
        print("\nDO YOU WANT TO CLEAN UP SOME FILES?")
        choice = input("Enter true for (Y/N): ").lower()
        if choice == 'true':
            for file in os.listdir():
                if file.startswith('temp_') or file == '.ds_store':
                    os.remove(file)
            for file in os.listdir():
                if file.startswith('old_dir_'):
                    shutil.rmtree(file)
            print("ALL TEMPS AND OLD FILES GONE!")
        
        
        
    except Exception as e:
        print(f"\n[Exception] Unable to get system info: {str(e)}")
        try:
            current_time = datetime.datetime.now()
            current_date = current_time.year
            print(f"\nCURRENT SYSTEM DATE: {current_date - 1} - {current_date}")
            print(f"{datetime.datetime.now()}")
        except Exception as e:
            print(f"\n[Exception] Can not print current date/time: {str(e)}")
        try:
            print(f"\n{hashlib.md5(f'{e}'.encode()).hexdigest()}")
            hash_object = hashlib.md5()
            hash_object.update(f'{e}'.encode())
            print(hashlib.md5(f'{e}'.encode()).hexdigest())
        except Exception as e:
            print(f"\n[Exception] Unable to convert exception: {str(e)}")

if __name__ == "__main__":
    main()