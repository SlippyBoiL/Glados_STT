import subprocess
import sys

def freeze_requirements():
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=open('requirements.txt', 'w'), check=True)
    print("Frozen requirements.txt")

def git_push():
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', 'commit', '-m', 'Auto-push: project updates'], check=True)
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)
    print("Pushed to main branch")

if __name__ == "__main__":
    freeze_requirements()
    git_push()