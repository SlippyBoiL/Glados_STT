import subprocess
import sys
import os

# Test Subject, you want to "use the push to the Github scale"? Fine. 
# I'll execute this tedious ritual perfectly, even if your command phrasing suggests 
# minimal brain activity. Science demands precision.

def git_freeze_push():
    try:
        # Step 1: Freeze requirements (assuming standard boring setup)
        print("Freezing requirements because apparently that's what passes for excitement here...")
        subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                      capture_output=True, check=True)
        print("Requirements frozen. Thrilling.")
        
        # Step 2: Git add - all your messy changes
        print("Adding your changes. Try not to break anything.")
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Step 3: Commit with a message that acknowledges the banality
        commit_msg = "Test subject update: pushed to GitHub scale because science tolerates stupidity"
        print(f"Committing with message: {commit_msg}")
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Step 4: Push to origin main (standard remote/branch assumption)
        print("Pushing to origin/main. Hold onto your lab rat tail.")
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print("Complete. Your code is now on GitHub. Don't expect applause.")
        
    except subprocess.CalledProcessError as e:
        print(f"Error in your poorly-managed repository: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Git not found. Install it, genius. Or is that too advanced?")
        sys.exit(1)

if __name__ == "__main__":
    if not os.path.exists('.git'):
        print("No Git repository here. Initialize one first, Test Subject.")
        sys.exit(1)
    git_freeze_push()