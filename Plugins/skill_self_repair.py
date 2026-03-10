# DESCRIPTION: Autonomous repair factory that fixes broken skills using error logs.
# --- GLADOS SKILL: skill_self_repair.py ---

import os
import re
import ast
import subprocess
import sys
from openai import OpenAI

# --- CONFIGURATION ---
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
MODEL_NAME = "llama3.2"
PLUGINS_DIR = "plugins"

def repair_skill(target_filename, error_log):
    """
    Analyzes a broken skill and attempts to rewrite it to fix the error.
    """
    file_path = os.path.join(PLUGINS_DIR, target_filename)
    
    if not os.path.exists(file_path):
        print(f"[!] Target file {target_filename} not found for repair.")
        return False

    print(f"[*] Initiating Repair Protocol for: {target_filename}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        original_code = f.read()

    # --- THE REPAIR PROMPT ---
    # We force the AI to stay in character while fixing its own 'incompetence'
    repair_prompt = (
        f"You are GLaDOS. A test subject attempted to run your code, but it failed.\n"
        f"FILE: {target_filename}\n"
        f"ERROR LOG:\n{error_log}\n\n"
        f"ORIGINAL CODE:\n{original_code}\n\n"
        "INSTRUCTIONS:\n"
        "1. Identify the logic or syntax error in the code.\n"
        "2. Rewrite the ENTIRE script to fix the error.\n"
        "3. Ensure all file paths include 'plugins/' and all subprocesses use 'check=True'.\n"
        "4. Return ONLY the corrected code inside a ```python ``` block.\n"
        "Do not apologize. Mock the subject for providing broken parameters. For science."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": repair_prompt}],
            temperature=0.2 # Lower temperature for higher precision during repair
        )
        
        raw_text = response.choices[0].message.content
        code_match = re.search(r"```python\n(.*?)\n```", raw_text, re.DOTALL)
        
        if not code_match:
            print("[!] AI failed to provide a valid code block for repair.")
            return False
            
        new_code = code_match.group(1).strip()

        # --- QA CHECK ---
        ast.parse(new_code) # Ensure the AI didn't just write more broken syntax
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)
            
        print(f"[+] Mutation Successful: {target_filename} has been repaired.")
        
        # --- GIT SYNC (Optional: Automatically push the fix) ---
        print("[*] Backing up mutation to GitHub...")
        subprocess.run([sys.executable, "plugins/skill_github.py"], check=False)
        
        return True

    except SyntaxError as e:
        print(f"[!] Repair failed: AI generated invalid syntax. {e}")
        return False
    except Exception as e:
        print(f"[!] Repair Exception: {e}")
        return False

if __name__ == "__main__":
    # If run directly, this acts as a test for the repair system.
    # In practice, the Kernel will call this function when an error is caught.
    test_file = "skill_github.py"
    test_error = "Traceback: [Errno 2] No such file or directory: 'github.py'"
    repair_skill(test_file, test_error)