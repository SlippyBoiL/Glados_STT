# --- GLADOS SKILL: skill_run_git_push.py ---

import subprocess
import sys
import os

def run_git_push():
    try:
        # Step 1: Generate requirements.txt
        print("Generating requirements.txt...")
        subprocess.run(["pip", "freeze", ">", "requirements.txt"], check=True)
        print("requirements.txt created.")
        
        # Step 2: Git add all files
        print("Running git add .")
        subprocess.run(["git", "add", "."], check=True)
        print("Files staged.")
        
        # Step 3: Git commit
        print("Running git commit -m 'Auto-Sync'")
        subprocess.run(["git", "commit", "-m", "Auto-Sync"], check=True)
        print("Committed changes.")
        
        # Step 4: Git push to main
        print("Running git push origin main")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Successfully pushed to GitHub main branch.")
        
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Git is not installed or not in PATH.")
        sys.exit(1)

if __name__ == "__main__":
    run_git_push()