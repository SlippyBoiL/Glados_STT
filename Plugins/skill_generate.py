# DESCRIPTION: A module to generate unique filenames and perform file operations.
# --- GLADOS SKILL: skill_generate.py ---

import getpass
import hashlib
import os
import uuid
import datetime
from time import sleep

def generate_unique_filename():
    return f"{hashlib.sha256(str(datetime.datetime.now()).encode('utf-8')).hexdigest()}_{uuid.uuid4().hex}"

def copy_file(source, destination):
    with open(source, 'rb') as src, open(destination, 'wb') as dst:
        dst.write(src.read())

def generate_password(length=12):
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(characters[ord(choice) - 87] for choice in [str(random.randint(0, 4)) for random in range(length)])

def main():
    password = generate_password()
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    while os.path.basename(destination := generate_unique_filename()) in [os.path.basename(existing) for existing in os.listdir(os.getcwd())]:
        sleep(1)
    
    os.makedirs(path := f".{hashed_password}", exist_ok=True)
    os.environ[f'HOME={hashed_password}'] = path
    os.environ['USER'] = os.environ.get('USER') or 'newuser'
    os.environ['PWD'] = os.getcwd()
    copy_file('whoami.py', os.path.join(path, '__main__.py'))

    os.system('echo "Password: '+password+' \nYour home path: '+path+ ' \n Your new user: '+os.environ['USER']+' \n Your current working directory: '+os.getcwd()+'" > README.md')
    print('Please save the README file and log in to your new environment.')

if __name__ == '__main__':
    main()
    print('Running "whoami.py" as', os.environ['USER'], '@', os.environ['HOME'])