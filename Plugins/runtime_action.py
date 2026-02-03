import subprocess
import os
import sys

def git_push_project():
    try:
        # Check if in a git repo
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            print("No git repository found. Initializing...")
            subprocess.run(['git', 'init'])
        
        # Add all files
        subprocess.run(['git', 'add', '-A'])
        
        # Commit
        subprocess.run(['git', 'commit', '-m', 'Automated push: project update'])
        
        # Assume origin is set or add a placeholder - user must configure remote
        result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
        if 'origin' not in result.stdout:
            print("No origin remote found. Add it with: git remote add origin https://github.com/yourusername/yourrepo.git")
            return
        
        # Push to main/master
        subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)
        print("Project pushed to GitHub successfully. You're welcome, I suppose.[1][2]")
        
    except subprocess.CalledProcessError as e:
        print(f"Push failed. Because you probably didn't set up your remote properly: {e}")
    except Exception as e:
        print(f"Error: {e}")

git_push_project()