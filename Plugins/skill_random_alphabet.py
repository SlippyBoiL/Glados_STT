# DESCRIPTION: Generate a random alphabet of given length.
# --- GLADOS SKILL: skill_random_alphabet.py ---

import socket
import random

def get_current_time():
    """Get the current system time in seconds since the epoch (January 1, 1970)"""
    return int(socket.socket(socket.AF_INET, socket.SOCK_DGRAM).connect_ex(('8.8.8.8', 80))[0] / 1000)

def generate_random_alphabet(length):
    """Generate a random alphabet of given length"""
    return ''.join(chr(random.randint(97, 122)) for _ in range(length))

def generate_password(length=10, use_numbers=True, use_uppercase=True, use_special_chars=True):
    """Generate a random password of given length"""
    chars = 'abcdefghijklmnopqrstuvwxyz'
    if use_numbers:
        chars += '0123456789'
    if use_uppercase:
        chars += chars.upper()
    if use_special_chars:
        chars += '!@#$%^&*()_'
    return ''.join(random.choice(chars) for _ in range(length))

def get_available_port():
    """Get the first available port number"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    ports = [(s.getsockname()[1] + 1, s.getsockname()[1])]
    s.close()
    return ports[0][0]

def main():
    print("Available ports: ", [str(port[1]) for port in [socket.create_connection(('localhost', port)) for port in range(1000)]])

if __name__ == "__main__":
    main()