# DESCRIPTION: Function to generate a random casual date between a defined start date and today.
# --- GLADOS SKILL: skill_generate_casual_date.py ---

import datetime
import json
import locale
import platform
import random
import socket
import string

def generate_casual_date():
    try:
        start_date = datetime.datetime(2000, 1, 1)
        end_date = datetime.datetime.today()
        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        casual_days = random.randint(0, days_between_dates)
        casual_dates = start_date + datetime.timedelta(days=casual_days)
        return casual_dates.strftime("%m-%d-%Y")
    except Exception as e:
        print(f"Failed to generate casual date: {str(e)}")
        return None

def generate_casual_password(length=10):
    alphanums = string.digits + string.ascii_letters
    return ''.join(random.choice(alphanums) for _ in range(length))

def get_system_info():
    version = platform.system()
    version = platform.release()
    version = f"{version}-{'-'.join(platform.release().split('-')[1:])}"
    return f"{version} - {platform.processor()}"

def get_user_data():
    try:
        with open('/etc/passwd', 'r') as passwd_file:
            lines = [line.strip() for line in passwd_file.readlines()[1:]]
        return json.dumps(lines).replace("'", "").replace('"', '')
    except:
        return 'Failed to load user data'

def print_info():
    casual_date = generate_casual_date()
    casual_password = generate_casual_password()
    system_info = get_system_info()
    user_data = get_user_data()
    print("System Info:")
    print(system_info)
    print("\nCasual Date:")
    print(f"Birth Date/Date of Interest: {casual_date}")
    print("\nCasual Password:")
    print(f"You: {casual_password} - Warning: Do not share!")
    print("\nUser Data:")
    print(user_data)

print_info()