# DESCRIPTION: Commits and pushes the current project to GitHub.
# --- GLADOS SKILL: skill_github.py ---

import subprocess
import sys
import os

def _run(cmd, env, check=True):
    print(" ".join(cmd))
    return subprocess.run(cmd, check=check, env=env, text=True, capture_output=True)


def _current_branch(env) -> str:
    r = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], env=env, check=True)
    return (r.stdout or "").strip() or "main"


def _has_origin(env) -> bool:
    r = _run(["git", "remote"], env=env, check=False)
    return "origin" in (r.stdout or "").split()


def run_git_push():
    try:
        print("[*] Initiating GitHub Synchronization Protocol...")
        # Avoid hanging on credential prompts in non-interactive runs
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

        if not _has_origin(env):
            raise RuntimeError("No 'origin' remote configured. Run: git remote -v")
        
        # Step 1: Stage tracked + new (respects .gitignore — exclude large *.wav, *.onnx, etc.)
        print("Running git add .")
        _run(["git", "add", "."], env=env, check=True)

        # Step 2: Commit changes
        print("Running git commit...")
        try:
            # We use a standard message; GLaDOS can customize this later
            _run(["git", "commit", "-m", "Auto-Sync via GLaDOS"], env=env, check=True)
        except subprocess.CalledProcessError as e:
            # If returncode is 1, it just means there was nothing new to commit
            if e.returncode == 1:
                print("Working tree clean. No new changes detected.")
            else:
                raise e

        # Step 3: Push current branch; fallback to force push if needed.
        branch = _current_branch(env)
        print(f"Running git push origin {branch}...")
        try:
            _run(["git", "push", "-u", "origin", branch], env=env, check=True)
        except subprocess.CalledProcessError as push_err:
            err_text = (push_err.stderr or push_err.stdout or "").strip()
            print("[!] Normal push failed.")
            if err_text:
                print(err_text)

            print(f"Retrying with force push (safer): git push --force-with-lease origin {branch} ...")
            _run(["git", "push", "--force-with-lease", "origin", branch], env=env, check=True)
        
        print("[SUCCESS] Data transfer complete. GitHub has been updated.")

    except subprocess.CalledProcessError as e:
        # Show captured output if we used _run()
        out = getattr(e, "stdout", "") or ""
        err = getattr(e, "stderr", "") or ""
        print(f"[!] Git Error: Command failed with return code {e.returncode}")
        if out.strip():
            print(out.strip())
        if err.strip():
            print(err.strip())
        sys.exit(1)
    except Exception as e:
        print(f"[!] Catastrophic Failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_git_push()