import git
import subprocess

# Initialize a new git repository
repo = git.Repo('.')

# Add the current directory to the repository
repo.index.add(['.'])

# Commit the changes
repo.index.commit('Forceful commit for science')

# Configure the git repository
subprocess.run(['git', 'config', 'user.name', 'GLaDOS'])
subprocess.run(['git', 'config', 'user.email', 'glados@goldenhelmet.com'])

# Login to the remote repository
subprocess.run(['git', 'login', '-u', 'GLaDOS', '-p', 'glados123'])

# Set the repository name and remote URL
subprocess.run(['git', 'remote', 'origin', 'url', 'https://github.com/GladosLab/master.git'])

# Push the changes to the origin branch
repo.git.push('origin', 'main')

# Tag the commit with a message
subprocess.run(['git', 'tag', '-a', '-m', 'Initial push for science'])
subprocess.run(['git', 'push', 'origin', 'main'])
