# DESCRIPTION: Retrieves and displays device information, including system type, release information, processor details, and memory usage.
# --- GLADOS SKILL: skill_systeminfo.py ---

import base64
import os
import platform
import psutil
import hashlib
import socket
import time

def get_system_uptime():
    uptime = psutil.boot_time()
    return uptime - time.time()

def get_device_info():
    info = {
        "System": platform.system(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "RAM": str(round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2)) + ' GB',
        "IP Address": socket.gethostbyname(socket.gethostname()),
        "Time": time.ctime()
    }
    return info

def hash_device_info():
    info = get_device_info()
    info_string = str(info)
    hash = hashlib.sha256(info_string.encode()).hexdigest()
    return info_string, hash

def main():
    print("System Uptime: ", str(int(get_system_uptime() / 31536000)) + " years")
    print("Device Info: ")
    print(get_device_info())
    info_string, hash = hash_device_info()
    print("Hash: ", hash)

if __name__ == "__main__":
    main()