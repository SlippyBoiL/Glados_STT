import subprocess
import sys
import os

# Change to the project directory if not already there; assuming current dir is project root
# Adjust path if needed: os.chdir('/path/to/your/project')

# Standard Git push sequence: assuming repo exists locally and remote is set
commands = [
    'git add -A',
    'git commit -m "Automated push from GLaDOS - because humans forget"',
    'git push origin main'  # Use 'master' if your default branch is master
]

for cmd in commands:
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {cmd}\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error with {cmd}: {e.stderr}")
        # If no remote or repo issues, common fixes:
        if "remote origin" in e.stderr or "not a git repository" in e.stderr:
            print("Reminder: Create GitHub repo first, then 'git remote add origin https://github.com/YOURUSERNAME/YOURREPO.git'")
        sys.exit(1)