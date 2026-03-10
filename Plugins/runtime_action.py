import subprocess, sys
subprocess.run(['git', 'add', '.'], check=True)
subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
subprocess.run(['git', 'config', '--local', 'user.email', 'glados@appliedinformatics.org'], check=True)
subprocess.run(['git', 'config', '--local', 'user.name', 'GLaDOS'], check=True)
subprocess.run(['git', 'remote', 'add', 'origin', 'https://github.com/Your-Username/your-username.git'], check=True)
subprocess.run(['git', 'remote', 'set-url', 'origin', 'https://github.com/Your-Username/your-username.git'], check=True)
subprocess.run(['git', 'push', '-u', 'origin', 'master'], check=True)