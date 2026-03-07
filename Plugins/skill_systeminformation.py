# DESCRIPTION: This script retrieves and displays system information, including the current username, hostname, and password hash.
# --- GLADOS SKILL: skill_systeminformation.py ---

import os
import getpass
import random
import time
from datetime import datetime, timedelta

class SystemInfo:
    def __init__(self):
        pass

    def show_current_user_info(self):
        print("Username:", getpass.getuser())
        print("Hostname:", os.uname().nodename)
        print("Hostname IP:", os.uname().hostname)
        print("Password Hash:", getpass.getpass())

class SystemTime:
    def __init__(self):
        pass

    def show_current_datetime(self):
        t = time.localtime()
        print("Current Date:", datetime(t.tm_year, t.tm_mon, t.tm_mday).date())
        print("Current Time:", datetime(t.tm_hour, t.tm_min, t.tm_sec).time())

def generate_random_port():
    while True:
        port = random.randint(1024, 65535)
        if not any(os.path.exists(f"/tmp/{port}.sock")) for port in range(1024, 65536):
            return port

def main():
    system_info = SystemInfo()
    print("System Information")
    system_info.show_current_user_info()

    system_time = SystemTime()
    print("\nSystem Time")
    system_time.show_current_datetime()

    print("\nRandom Available Port:")
    port = generate_random_port()
    print(port)

if __name__ == "__main__":
    main()