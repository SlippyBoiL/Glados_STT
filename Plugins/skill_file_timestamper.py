# DESCRIPTION: This script renames the current file with a timestamp and attempts to prevent file name conflicts.
# --- GLADOS SKILL: skill_file_timestamper.py ---

import os
import datetime
import uuid

def skill_file_timestamper():
    current_time = datetime.datetime.now()
    file_timestamp = str(current_time).replace(':', '')
    new_filename = f"{os.path.basename(__file__)}_{file_timestamp}.txt"

    i = 1
    while os.path.exists(new_filename):
        new_filename = f"{os.path.basename(__file__)}_{uuid.uuid4().hex}_{i}.txt"
        i += 1

    os.rename(__file__, new_filename)

if __name__ == "__main__":
    skill_file_timestamper()


This script will rename the current Python script to include a timestamp and a unique identifier. The new filename will be saved as a .txt file. If a file with the same name already exists, the script will keep adding a unique identifier until it finds a name that is not taken.