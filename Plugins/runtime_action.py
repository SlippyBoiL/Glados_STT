import subprocess

# Initialize GitHub repository
github_repo = "https://github.com/your-username/your-repo-name.git"

# Navigate to the project directory
subprocess.run(["git", "init"], cwd=".")
subprocess.run(["git", "add", "."], cwd=".")

# Set the Git username and email
subprocess.run(["git", "config", "--local", "user.name", "Your-Name"], cwd=".")
subprocess.run(["git", "config", "--local", "user.email", "your-email@example.com"], cwd=".")

#Commit the changes
subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=".")

#Link the repository to GitHub
subprocess.run(["git", "remote", "add", "origin", github_repo], cwd=".")
subprocess.run(["git", "push", "-u", "origin", "main"], cwd=".")

# Notify the GitHub server of the push
subprocess.run(["git", " Push origin main:main"], cwd=".")