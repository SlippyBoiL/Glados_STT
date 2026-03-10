# DESCRIPTION: A script that retrieves and displays the current git status.
# --- GLADOS SKILL: skill_create_git_status.py ---

import os
import time
import random
import hashlib
import secrets
import datetime

def generate_secret_token(length=16):
    return ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                   for _ in range(length))

def get_current_git_status():
    current_git_status = os.popen("git status").read().strip()
    return current_git_status

def current_project_info():
    project_info = {
        'root_dir': os.getcwd(),
        'working_dir': os.getcwd(),
        'project_name': os.path.basename(os.getcwd()),
        'git_status': get_current_git_status()
    }
    return project_info

def get_files_in_directory(path):
    return os.listdir(path)

def file_timestamp(path, format="%Y-%m-%d %H:%M:%S"):
    last_modified = os.path.getmtime(path)
    timestamp = datetime.datetime.fromtimestamp(last_modified)
    timestamp = timestamp.strftime(format)
    return timestamp

def generate_alphanumeric_string(length):
    return ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                   for _ in range(length))

def get_ip_address():
    return os.popen('ip addr show dev eth0 | grep "inet " | awk \'{print $2}'.') read()

def get_disk_usage(path):
    total, free, _, _ = os.popen('du -h --max-depth 1 {}'.format(path)).read().strip().split()[0].split('/')
    return total, free

def generate_cipher():
    key = str(secrets.token_hex(8))
    cipher = {}
    for char in 'abcdefghijklmnopqrstuvwxyz':
        cipher[char] = chr((ord(char) + ord(key[0])) % 97)
    return cipher

def create_md5_hash(text):
    hash = hashlib.md5()
    hash.update(text.encode())
    return hash.hexdigest()

def reverse_text(text):
    return text[::-1]

def convert_to_binary(text):
    return ''.join(format(ord(char), '08b') for char in text)

def convert_back_to_text(binary):
    return bytes([int(byte, 2) for byte in binary]).decode()

def get_memory_usage():
    process = os.popen('ps -eo rss,cmd').read()
    for line in process.split('\n'):
        if 'python' in line[8:]:
            lines = line.split(' ', 10)
            memory_usage = int(lines[1])
            return memory_usage

def get_system_uptime():
    current_date = datetime.datetime.now()
    current_time = current_date.timestamp()
    system_uptime = int(current_time // 60)
    return system_uptime

def system_resources_info():
    total, free, _, _ = os.popen('du -h --max-depth 1 /').read().strip().split()[0].split('/')
    process = os.popen('ps -eo rss,cmd').read()
    network_usage = 0
    network_info = os.popen('cat /proc/net/dev').read()
    for line in network_info.split('\n'):
        if 'eth0' in line.split()[0]:
            network_usage = int(line.split()[1].split('/')[0].replace(',', ''))
    return total, free, network_usage

if __name__ == "__main__":
    # Test usage
    print(current_project_info)