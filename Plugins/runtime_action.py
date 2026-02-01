import subprocess
import sys
import os

# Step 1: Freeze requirements (if requirements.txt exists)
if os.path.exists('requirements.txt'):
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=open('requirements.txt', 'w'), check=True)
    print("Requirements frozen and updated.")

# Step 2: Add all changes
subprocess.run(['git', 'add', '-A'], check=True)
print("All changes staged.")

# Step 3: Commit with a standard message
subprocess.run(['git', 'commit', '-m', 'Auto-commit: Project updates'], check=True)
print("Changes committed.")

# Step 4: Push to GitHub (assumes remote 'origin' is set; uses main branch)
subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)
print("Project pushed to GitHub successfully.")

# Step 5: Git workflow complete - add, commit, push
print("Git workflow completed: added, committed, and pushed to origin/main.")