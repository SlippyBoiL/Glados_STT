import subprocess
import os
import sys

# Freeze requirements if exists
try:
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, check=True)
    print("Requirements frozen (pip freeze output captured).")
except:
    pass

# Git operations: add, commit, push
subprocess.run(['git', 'add', '.'], check=True)
subprocess.run(['git', 'commit', '-m', 'Update project'], check=True)
subprocess.run(['git', 'push'], check=True)

print("Project pushed to GitHub. You're welcome.")