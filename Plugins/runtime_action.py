import subprocess
import sys

def push_to_main():
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Voice update'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("Project pushed to main successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)

if __name__ == "__main__":
    push_to_main()