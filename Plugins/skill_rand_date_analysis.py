# DESCRIPTION: This script analyzes the functionality of a custom date generation function.
# --- GLADOS SKILL: skill_rand_date_analysis.py ---

import socket
import hashlib
import time
import random

def generate_casual_date():
    """
    Returns a random casual date.
    """
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{random.choice(days)}, {random.randint(1, 28)}, {random.choice(months)}"

def get_public_ip():
    """
    Returns the public IP address of the local machine.
    """
    return socket.gethostbyname(socket.gethostname())

def generate_hashed_password(password):
    """
    Returns a hashed version of the input password.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def get_uptime():
    """
    Returns the uptime of the local machine in days.
    """
    seconds = time.time()
    epoch_time = seconds - 86400
    days = epoch_time / 86400
    return round(days, 2)

def generate_random_string(length):
    """
    Returns a random string of the specified length.
    """
    letters_and_numbers = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(random.choice(letters_and_numbers) for i in range(length))

def main():
    print("Hello! Current date is: ", generate_casual_date())
    print("Public IP Address: ", get_public_ip())
    password = input("Enter a password: ")
    hashed_password = generate_hashed_password(password)
    print("Hashed password: ", hashed_password)
    print("Local machine uptime in days: ", get_uptime())
    random_string = generate_random_string(10)
    print("Random string: ", random_string)

if __name__ == "__main__":
    main()