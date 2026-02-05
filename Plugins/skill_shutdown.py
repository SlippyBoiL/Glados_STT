# DESCRIPTION: Schedules or aborts a system shutdown.
# --- GLADOS SKILL: skill_shutdown.py ---

import subprocess
import sys

def manage_power(action="abort"):
    # Pass 'schedule' or 'abort' as arguments if calling via CLI
    if len(sys.argv) > 1: action = sys.argv[1]
    
    if "schedule" in action:
        subprocess.run("shutdown /s /t 60", shell=True)
        return "Shutdown sequence initiated. T-minus 60 seconds."
    elif "abort" in action:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown sequence aborted. You got lucky."
    else:
        return "Invalid command."

if __name__ == "__main__":
    # Default behavior for testing is abort to be safe
    print(manage_power("abort"))