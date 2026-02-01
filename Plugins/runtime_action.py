import subprocess
import sys
import os

# Step 1: Freeze requirements (if requirements.txt exists)
if os.path.exists('requirements.txt'):
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=open('requirements.txt', 'w'), check=True)
    print("Requirements frozen to requirements.txt")

# Step 2: Git add all changes
subprocess.run(['git', 'add', '-A'], check=True)
print("All changes staged.")

# Step 3: Git commit
subprocess.run(['git', 'commit', '-m', f"Project update - {os.popen('git status --porcelain').read().strip() or 'general changes'}"], check=True)
print("Changes committed.")

# Step 4: Git push to origin (assumes remote origin is set)
subprocess.run(['git', 'push'], check=True)
print("Project pushed to GitHub.")

# Step 5: Git status summary
status = subprocess.run(['git', 'status'], capture_output=True, text=True)
print("Current git status:\n", status.stdout)

print("Git workflow complete: requirements frozen, added, committed, and pushed to GitHub.[1][2][3]")