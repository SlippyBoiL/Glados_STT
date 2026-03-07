# DESCRIPTION: A class to log skills with datetime stamp and message.
# --- GLADOS SKILL: skill_logging.py ---

import datetime
import time

class SkillNewLog:
    def __new__(cls, timestamp_format='%Y-%m-%d %H:%M:%S'):
        self.timestamp_format = timestamp_format
        return super().__new__(cls)

    def record(self, message, duration=1, separator=', '):
        now = datetime.datetime.now()
        record = f"{now.strftime(self.timestamp_format)} - {message}:"
        print(f"[{record}]".ljust(len(record) + 10), end=' ')
        elapsed_time = time.strftime("%H:%M:%S", time.gmtime(timestamp=now.timestamp() + duration * 60))
        print(f"({elapsed_time[:-2]})", end=' ')
        print(separator.join([f"{record[:-15:]}", f"{elapsed_time}"]))


import os
os.environ['LANG'] = 'en_US'

new_log = SkillNewLog()
new_log.record("Started")
new_log.record("Logged-in user is: whoami")
new_log.record("Elapsed time is: 1 second")
new_log.record("Elapsed time is: 2 seconds", duration=2)
new_log.record("Elapsed time is: 5 seconds", separator='|')