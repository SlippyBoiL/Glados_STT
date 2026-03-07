# DESCRIPTION: Generates an encrypted file path using SHA-256 hash and base64 encoding.
# --- GLADOS SKILL: skill_generate_encrypted_file_path.py ---

#!/usr/bin/env python
import hashlib
import base64
import time
import os
import datetime

def generate_encrypted_file_path(file_name):
    """
    Generate an encrypted file path using SHA-256 hash and base64 encoding.
    """
    file_hash = hashlib.sha256(open(file_name, 'rb').read()).digest()
    encrypted_path = base64.b64encode(file_hash).decode('utf-8') + ':' + file_name
    return encrypted_path

def encrypt_file(file_name):
    """
    Encrypt a file using SHA-256 hashing and base64 encoding.
    """
    file_path = generate_encrypted_file_path(file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    return file_path

def decrypt_file(file_name, encrypted_file_path):
    """
    Decrypt a file using SHA-256 hashing and base64 decoding.
    """
    encrypted_file_path = encrypted_file_path[1:]
    try:
        file_hash = encrypted_file_path.encode('utf-8')
    except UnicodeDecodeError:
        return "Invalid encrypted file path."
    file_hash = base64.b64decode(file_hash)
    file_path = open(file_name + ".sha256", 'wb')
    file_path.write(file_hash)
    return file_path

def main():
    file_name = input("Enter a file name: ")
    action = input("Do you want to (E)ncrypt, (D)ecrypt, or (Q)uit? ")
    if action.upper() == "E":
        print("Encrypting...")
        encrypted_file_path = encrypt_file(file_name)
        print("File path:", encrypted_file_path)
    elif action.upper() == "D":
        file_path = decrypt_file(file_name, file_name + ".sha256")
        if file_path:
            print("File path:", file_path.name)
        else:
            print("Encryption key not found.")
    elif action.upper() == "Q":
        print("Exiting...")
    else:
        print("Invalid action.")

if __name__ == "__main__":
    os.system('clear')
    main()


This script provides an interactive tool for encrypting files by generating an SHA-256 hash of each file, then encoding it in base64 and appending it to the file path. It also decrypts the file using the same hashing and encoding method.