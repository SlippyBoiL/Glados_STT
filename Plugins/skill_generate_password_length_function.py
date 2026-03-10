# DESCRIPTION: A Python function to generate a random password of a specified length using ASCII letters, digits, and punctuation.
# --- GLADOS SKILL: skill_generate_password_length_function.py ---

import random
import string
import os
import time

def generate_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def create_file(path, content):
    with open(path, 'w') as file:
        file.write(content)

def generate_temporary_file():
    temp_dir = os.path.join(os.getcwd(), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, str(time.time()) +('.txt'))
    create_file(file_path, '')
    return file_path

def move_file(path1, path2):
    if os.path.exists(path1):
        os.rename(path1, path2)

def generate_unique_filename(extension):
    temp_dir = os.path.join(os.getcwd(), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    filename = str(time.time()) + extension
    file_path = os.path.join(temp_dir, filename)
    return file_path

def generate_random_quote():
    adjectives = ['great', 'good', 'amazing', 'awesome', 'okay']
    nouns = ['cat', 'dog', 'car', 'house', 'tree']
    return f"{random.choice(adjectives)} {random.choice(nouns)}"

def get_files_under_directory(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

def main():
    print(generate_random_quote())
    print(generate_temporary_file())
    print(generate_unique_filename('.txt'))
    print(move_file('./file.txt', generate_unique_filename('.txt')))
    print('Files found under the current directory:')
    for file in get_files_under_directory('./'):
        print(file)

if __name__ == "__main__":
    main()