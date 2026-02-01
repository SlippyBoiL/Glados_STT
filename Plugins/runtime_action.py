import subprocess
import sys

# Freeze requirements
subprocess.run([sys.executable, '-m', 'pip', 'freeze', '>', 'requirements.txt'])

# Git operations: add, commit, push
subprocess.run(['git', 'add', '.'])
subprocess.run(['git', 'commit', '-m', 'Auto-commit: Freeze reqs and updates'])
subprocess.run(['git', 'push'])