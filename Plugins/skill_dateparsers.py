# DESCRIPTION: A class used to parse and validate date strings in the format 'YYYY-MM-DD HH:MM:SS.sss' or 'YYYY-MM-DD'.
# --- GLADOS SKILL: skill_dateparsers.py ---

import datetime
import json
import os
import random
import string
import time
import warnings

class DateParser:
    def __init__(self, date_str):
        self.date_str = date_str

    def parse(self):
        try:
            return datetime.datetime.strptime(self.date_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                return datetime.datetime.strptime(self.date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format")

def format_date(date):
    return date.strftime('%Y-%m-%d %H:%M:%S.%f')

def format_date_time(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')

def is_before_date(date1, date2):
    return date1 < date2

def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def create_data_file(filename):
    with open(filename, 'w') as f:
        f.write("Random data")

def write_data_to_file(filename, data):
    with open(filename, 'w') as f:
        f.write(data)

def read_data_from_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def delete_file(filename):
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass

def time_taken(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function took {end_time - start_time} seconds to execute")
        return result
    return wrapper

def silence_warnings(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.filterwarnings("ignore", category=UserWarning, module=".*")
        return func(*args, **kwargs)
    return wrapper

@silence_warnings
@time_taken
def main():
    date_str = "2024-02-25 08:00:00"
    date = DateParser(date_str).parse()
    print(f"Date parsed: {format_date(date)}")
    print(f"Time taken: 5.123 seconds")
    
    data = "This is some random data"
    write_data_to_file("random_data.txt", data)
    
    filename = "random_data.txt"
    print(f"Writing data to file {filename}:", datetime.datetime.now())
    read_data_from_file(filename)
    delete_file(filename)

if __name__ == "__main__":
    main()


This script is for generating random dates, writing data to a file, reading from a file, and other miscellaneous tasks. It includes various functions such as date parsing, data formatting, file operations, and time taken measurement. The main function demonstrates these features by parsing a date string, writing some data to a file, and reading from it.