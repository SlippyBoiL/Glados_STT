import subprocess
import sys
import os

# Check if in a git repo, if not, this is your fault for not setting up properly
try:
    subprocess.run(['git', 'status'], check=True, capture_output=True)
    print("Local repo detected. Attempting push...")
except subprocess.CalledProcessError:
    print("No git repo found. Did you even init? Pathetic.")
    sys.exit(1)

# Assume standard setup, because expecting you to have one is optimistic
subprocess.run(['git', 'add', '.'], check=True)
subprocess.run(['git', 'commit', '-m', 'Dump of test subject\'s mess'], capture_output=True)
subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)

print("Pushed. If it failed, check your remote. Or your life choices.")