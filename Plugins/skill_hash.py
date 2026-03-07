# DESCRIPTION: Generation of a SHA256 checksum for a given file.
# --- GLADOS SKILL: skill_hash.py ---

import hashlib
import socket
import time
import uuid

def generate_random_string(length=8):
    """Generate a random string of alphanumeric characters"""
    characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ0123456789'
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def generate_checksum(file_path):
    """Generate a checksum of a given file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read and update the hash object with chunks of the file
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    # Return the hexadecimal representation of the hash
    return sha256.hexdigest()

def get_local_ip():
    """Get the current local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def update_system_timestamp():
    """Get the current system timestamp and return the formatted date string"""
    current_timestamp = time.time()
    timestamp_string = "{:%Y-%m-%d %H:%M:%S}".format(time.localtime(int(current_timestamp)))
    return timestamp_string

if __name__ == "__main__":
    # Generate a random password
    print("Random Password:")
    print(generate_random_string())

    # Generate a checksum
    file_path = 'example.txt'
    print("\nCheck Sum of '{}'".format(file_path))
    print(generate_checksum(file_path))

    # Get the local IP address
    print("\nLocal IP Address:")
    print(get_local_ip())

    # Get and display the system timestamp
    print("\nSystem Timestamp:")
    print(update_system_timestamp())