# DESCRIPTION: Automatically imports skills from 'new_skills.txt' without asking.
# --- GLADOS SKILL: skill_auto_import.py ---

import os
import re
import time

# CONFIGURATION
TARGET_FILE = "new_skills.txt"
PLUGINS_DIR = "plugins"

def auto_import():
    """
    Looks for 'new_skills.txt' in the main folder and imports everything found.
    No input required.
    """
    if not os.path.exists(TARGET_FILE):
        return f"FAILURE: Could not find '{TARGET_FILE}'. Please create this file in the main folder."

    try:
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"READ ERROR: {e}"

    # Regex to find code blocks
    pattern = r"```(?:python)?\s*\n(.*?)\n\s*```"
    matches = re.findall(pattern, content, re.DOTALL)

    if not matches:
        return "Zero code blocks found. The file is empty or formatted by an idiot."

    saved_count = 0
    errors = 0

    for code in matches:
        code = code.strip()
        if not code: continue

        # Extract function name
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        
        if name_match:
            func_name = name_match.group(1)
            filename = f"skill_{func_name}.py"
        else:
            filename = f"skill_import_{int(time.time())}_{saved_count}.py"

        # Unique filename check
        base_name = filename
        counter = 1
        while os.path.exists(os.path.join(PLUGINS_DIR, base_name)):
            base_name = f"{filename.replace('.py', '')}_{counter}.py"
            counter += 1
        
        final_filename = base_name
        full_path = os.path.join(PLUGINS_DIR, final_filename)

        # Add Header
        header = ""
        if "# DESCRIPTION:" not in code:
            header = f"# DESCRIPTION: Auto-Imported Skill.\n# --- GLADOS SKILL: {final_filename} ---\n\n"

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(header + code)
            saved_count += 1
        except:
            errors += 1

    return f"Auto-Import Complete. {saved_count} skills extracted. {errors} errors."

if __name__ == "__main__":
    print(auto_import())