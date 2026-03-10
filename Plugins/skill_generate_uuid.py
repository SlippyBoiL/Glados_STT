# DESCRIPTION: Generates a unique identifier by combining the current time and random numbers.
# --- GLADOS SKILL: skill_generate_uuid.py ---

import socket
import time
import random

# Function to get the system's MAC address
def get_mac_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    mac_address = s.getsockname()[0]
    s.close()
    return mac_address

# Function to generate a random UUID
def generate_uuid():
    return f"{time.time():.6f}{random.randint(1, 1000000)}/{random.randint(1, 1000000)}/{random.randint(1, 1000000)}"

# Function to measure the execution time of a given function
def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time:.6f} seconds")
        return result
    return wrapper

# Example usage:
if __name__ == "__main__":
    mac_address = get_mac_address()
    print(f"MAC Address: {mac_address}")
    uuid = generate_uuid()
    print(f"Generated UUID: {uuid}")