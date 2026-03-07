# DESCRIPTION: Parses a text file for code blocks and creates new skills.
# --- GLADOS SKILL: skill_bulk_import.py ---

import os
import re
import time

PLUGINS_DIR = "plugins"

def import_skills_from_file(file_path):
    """
    Reads a text file, finds markdown code blocks, and saves them as skills.
    """
    if not os.path.exists(file_path):
        return f"File not found: {file_path}. precise coordinates are required."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"Unable to read file. Error: {e}"

    # Regex to find code blocks (```python ... ``` or just ``` ... ```)
    # capturing the content inside the backticks
    pattern = r"```(?:python)?\s*\n(.*?)\n\s*```"
    matches = re.findall(pattern, content, re.DOTALL)

    if not matches:
        return "No code blocks detected. Your formatting is likely incompetent."

    saved_count = 0
    errors = 0
    new_files = []

    for code in matches:
        code = code.strip()
        if not code: continue

        # Attempt to find a function name to use as the filename
        # Looks for: def function_name(
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        
        if name_match:
            func_name = name_match.group(1)
            filename = f"skill_{func_name}.py"
        else:
            # Fallback for scripts without functions
            filename = f"skill_import_{int(time.time())}_{saved_count}.py"

        # Check for collision and rename if necessary
        base_name = filename
        counter = 1
        while os.path.exists(os.path.join(PLUGINS_DIR, base_name)):
            base_name = f"{filename.replace('.py', '')}_{counter}.py"
            counter += 1
        
        filename = base_name
        full_path = os.path.join(PLUGINS_DIR, filename)

        # Add the Header if it's missing
        header = ""
        if "# DESCRIPTION:" not in code:
            header = f"# DESCRIPTION: Imported via Bulk Loader.\n# --- GLADOS SKILL: {filename} ---\n\n"

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(header + code)
            new_files.append(filename)
            saved_count += 1
        except:
            errors += 1

    result_msg = f"Import complete. {saved_count} new protocols active."
    if errors > 0:
        result_msg += f" {errors} failures occurred."
    
    return result_msg

if __name__ == "__main__":
    # Test path - replace with a real path to test manually
    import sys
    if len(sys.argv) > 1:
        print(import_skills_from_file(sys.argv[1]))
    else:
        print("Usage: python skill_bulk_import.py <path_to_txt_file>")