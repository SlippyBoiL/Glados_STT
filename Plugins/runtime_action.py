import subprocess
import sys
import os

# Freeze requirements if exists
try:
    subprocess.run([sys.executable, '-m', 'pip', 'freeze', '> requirements.txt'], check=True, cwd=os.getcwd())
except:
    pass

# Git operations: add, commit, push
subprocess.run(['git', 'add', '.'], check=True, cwd=os.getcwd())
subprocess.run(['git', 'commit', '-m', 'Auto-push: Project updated'], check=True, cwd=os.getcwd())
subprocess.run(['git', 'push'], check=True, cwd=os.getcwd())