# DESCRIPTION: Checks internet latency via Google DNS.
# --- GLADOS SKILL: skill_ping.py ---

import subprocess
import re

def check_ping():
    try:
        # Windows ping command (1 ping)
        output = subprocess.check_output(["ping", "-n", "1", "8.8.8.8"]).decode('utf-8')
        match = re.search(r"time=(\d+)ms", output)
        if match:
            return f"Ping to Grid: {match.group(1)}ms. Acceptable."
        return "Ping failed. The internet is broken. Or you are."
    except:
        return "Connection severed."

if __name__ == "__main__":
    print(check_ping())