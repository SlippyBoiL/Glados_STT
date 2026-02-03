import subprocess
import sys
import os

# Freeze requirements if requirements.txt exists
if os.path.exists('requirements.txt'):
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=open('requirements.txt', 'w'), check=True)

# Git operations: add, commit, push
subprocess.run(['git', 'add', '.'], check=True)
subprocess.run(['git', 'commit', '-m', 'Update project'], check=True)
subprocess.run(['git', 'push'], check=True)

print("Project pushed to GitHub. Because apparently you can't manage that yourself.")