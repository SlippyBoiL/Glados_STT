import subprocess, sys
subprocess.run(['git', 'add', '.'])
subprocess.run(['git', 'commit', '-m', 'Freeze reqs, add, commit, push'])
subprocess.run(['git', 'push'])