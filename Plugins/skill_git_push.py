# --- GLADOS SKILL: skill_git_push.py ---

# GIT: 'Push to main' - Executing save skill + git workflow for weather_skill_v2.py

import subprocess
import sys
import os

# Step 1: Save skill as persistent file using pickle (best practice)[1][3]
import pickle
import joblib

# Create and serialize the weather skill
skill = KissimmeeWeather()  # From previous v2 code

# Save model/skill object (handles complex objects better than pickle)[1][3]
filename = 'weather_skill_kissimmee.joblib'
joblib.dump(skill, filename)
print(f"[SAVED] Skill persisted: {filename}")

# Step 2: Create requirements.txt freeze
reqs = [
    'requests==2.31.0',  # For API calls
    'joblib==1.4.2',     # Model persistence
    'urllib3==2.2.2'     # HTTP
]
with open('requirements.txt', 'w') as f:
    f.write('\n'.join(reqs))
print("[FROZEN] requirements.txt created")

# Step 3: Git workflow - add, commit, push to main
def git_push():
    commands = [
        ['git', 'add', '.'],
        ['git', 'commit', '-m', 'feat: add kissimmee weather skill v2 with live API + persistence'],
        ['git', 'push', 'origin', 'main']
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"[GIT] {' '.join(cmd)}: SUCCESS")
        except subprocess.CalledProcessError as e:
            print(f"[GIT ERROR] {' '.join(cmd)}: {e.stderr}")
            return False
    return True

# Execute git push
if git_push():
    print("\n[GIT PUSH COMPLETE] weather_skill_kissimmee.joblib + requirements.txt -> main branch")
    print("Live weather API integrated. Load anytime: skill = joblib.load('weather_skill_kissimmee.joblib')")
else:
    print("[FAILED] Git push error - check repo status")

# Usage example post-deploy
print("\n[DEPLOYED SKILL TEST]")
loaded_skill = joblib.load(filename)
print(loaded_skill.get_current_weather())