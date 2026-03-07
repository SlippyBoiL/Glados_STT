# DESCRIPTION: Commits and pushes the current project to GitHub.
# --- GLADOS SKILL: skill_push_to_the_github.py ---

import subprocess
import sys
import os


def _generate_requirements_txt():
    """Safely generate requirements.txt using pip freeze."""
    print("Generating requirements.txt...")
    try:
        # Use the running interpreter and capture output instead of relying on shell redirection.
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
        )
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.write(result.stdout)
        print("requirements.txt created.")
    except subprocess.CalledProcessError as e:
        print(f"pip freeze failed: {e}")
        # Not fatal for git push; continue anyway.


def run_git_push():
    try:
        # Step 1: Generate requirements.txt
        _generate_requirements_txt()

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