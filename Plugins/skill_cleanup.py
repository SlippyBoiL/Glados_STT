# DESCRIPTION: Cleans up temporary files in the Windows TEMP directory.
# --- GLADOS SKILL: skill_cleanup.py ---

import os
import shutil

def cleanup_temp():
    temp_dir = os.environ.get('TEMP')
    if not temp_dir: return "Could not locate TEMP directory."
    
    deleted = 0
    errors = 0
    
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                deleted += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted += 1
        except:
            errors += 1
            
    return f"Incineration complete. {deleted} items removed. {errors} items stubbornly refused to die."

if __name__ == "__main__":
    print(cleanup_temp())