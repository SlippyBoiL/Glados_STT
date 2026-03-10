# DESCRIPTION: This script simulates generating random to-do list items in a loop.
# --- GLADOS SKILL: skill_generate_todo_list.py ---

import time
import random
import hashlib
import threading

# Function to generate a random 'todo' list item
def todo_list_item():
    while True:
        items = {
            'Buy': ['milk', 'eggs', 'chicken'],
            'Grocery': ['apples', 'bananas'],
            'Errands': ['go to laundromat', 'post letter']
        }
        category = random.choice(list(items.keys()))
        item = random.choice(items[category])
        print(f"TODO: Buy {item}")
        time.sleep(60)

# Function to generate a single random alphanumeric code
def random_code(length=6):
    letters_and_digits = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(letters_and_digits) for _ in range(length))

# Function to generate and print a single random password
def generate_password(length=10):
    letters_and_digits = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    other = '!"$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    password = ''.join(random.choice(letters_and_digits) for _ in range(length//2))
    for char in random.choice(['!', '@', '#', '$', '%', '&', '\'', '(', ')']):
        password += random.choice(other)
    print(password)

# Function to simulate a browser refresh
def browser_refresh():
    print("Browser refresh initiated")
    time.sleep(random.random() * 10)
    print("Browser refresh complete")

# Function to verify system time
def verify_time():
    start = time.time()
    while True:
        print(f"Current time: {time.ctime()}")
        print(f"Time elapsed: {time.time() - start} seconds")
        time.sleep(1)

# Function to generate a new SHA-256 hash of a string
def hash_string(input_string):
    return int(hashlib.sha256(input_string.encode()).hexdigest(), 16)

# Function to find open ports
def open_ports():
    for port in range(1, 1025):
        if port in [22, 5432, 80, 443]:
            continue
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect(('127.0.0.1', port))
            if result:
                print(f"Port: {port} is open")
                sock.close()
        except Exception as e:
            pass

# Function to check system CPU usage
def cpu_usage():
    while True:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            print(f"CPU: {cpu_percent}%")
            time.sleep(1)
        except Exception as e:
            pass

if __name__ == "__main__":
    # Thread to generate a random todo list item every 20 seconds
    threading.Thread(target=todo_list_item, daemon=True).start()

    # Thread to generate a single random code every 5 minutes
    threading.Thread(target=random_code, daemon=True).start()

    # Thread to generate and print a random password every 10 minutes
    threading.Thread(target=generate_password, daemon=True).start();

    # Thread to simulate a browser refresh
    threading.Thread(target=browser_refresh, daemon=True).start()

    # Thread to verify system time every minute
    threading.Thread(target=verify_time, daemon=True).start()

    # Thread to generate a new SHA-256 hash of a string every 10 minutes
    threading.Thread(target=hash_string, daemon=True).start()

    # Thread to find open ports every 30 minutes
    threading.Thread(target=open_ports, daemon=True).start()

    # Thread to check system CPU usage every minute
    threading.Thread(target=cpu_usage, daemon=True).start()