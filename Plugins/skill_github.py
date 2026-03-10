# DESCRIPTION: Commits and pushes the current project to GitHub.
# --- GLADOS SKILL: skill_github.py ---

import subprocess
import sys
import os

def run_git_push():
    try:
        print("[*] Initiating GitHub Synchronization Protocol...")
        
        # Step 1: Stage all changes
        print("Running git add .")
        subprocess.run(["git", "add", "."], check=True)

        # Step 2: Commit changes
        print("Running git commit...")
        try:
            # We use a standard message; GLaDOS can customize this later
            subprocess.run(["git", "commit", "-m", "Auto-Sync via GLaDOS"], check=True)
        except subprocess.CalledProcessError as e:
            # If returncode is 1, it just means there was nothing new to commit
            if e.returncode == 1:
                print("Working tree clean. No new changes detected.")
            else:
                raise e

        # Step 3: Force Push to 'main'
        # This ensures the remote matches your local state exactly
        print("Running git push -f origin main...")
        subprocess.run(["git", "push", "-f", "origin", "main"], check=True)
        
        print("[SUCCESS] Data transfer complete. GitHub has been updated.")

    except subprocess.CalledProcessError as e:
        print(f"[!] Git Error: Command failed with return code {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Catastrophic Failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_git_push()