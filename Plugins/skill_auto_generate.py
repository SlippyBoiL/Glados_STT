import os
import re
from openai import OpenAI

# --- LOCAL AI SETUP ---
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
MODEL_NAME = "llama3.2"
PLUGINS_DIR = "Plugins"

def get_existing_skills():
    """Checks the inventory of current skills to prevent duplicates."""
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)
    return [f for f in os.listdir(PLUGINS_DIR) if f.endswith(".py")]

def draft_and_assemble_skill():
    """The core automation pipeline that drafts and saves new code."""
    inventory = get_existing_skills()
    inventory_str = ", ".join(inventory) if inventory else "None"
    
    print(f"\n[*] Current inventory: {len(inventory)} skills found.")
    print("[*] Drafting new skill...")
    
    # PROMPT 1: Generate the raw code
    messages = [
        {"role": "system", "content": "You are an expert Python developer. Write a single, self-contained Python script for a helpful OS utility, math function, or API fetcher. DO NOT write code that requires third-party libraries not in standard Python. ONLY output valid Python code. No explanations. No markdown."},
        {"role": "user", "content": f"Existing skills: {inventory_str}.\nWrite a completely new, unique Python script. Do not duplicate existing skills."}
    ]
    
    try:
        print("    -> Thinking of a new concept...")
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        raw_code = response.choices[0].message.content
        
        # Aggressive markdown stripping
        code = re.sub(r"```[pP]ython\n(.*?)```", r"\1", raw_code, flags=re.DOTALL)
        code = re.sub(r"```(.*?)```", r"\1", code, flags=re.DOTALL).strip()
        
        # PROMPT 2: Have the AI name and describe its own creation
        print("    -> Generating accurate file metadata...")
        naming_messages = [
            {"role": "system", "content": "You are a naming assistant. Read the code and output exactly two lines. Line 1: 'FILENAME: skill_<name>.py'. Line 2: 'DESCRIPTION: <1 sentence description>'."},
            {"role": "user", "content": f"Analyze this code:\n\n{code[:500]}"}
        ]
        
        name_response = client.chat.completions.create(model=MODEL_NAME, messages=naming_messages)
        meta_text = name_response.choices[0].message.content
        
        # --- THE BULLETPROOF REGEX PARSER ---
        # Hunt for a word starting with 'skill_' and ending with '.py'
        filename_match = re.search(r'(skill_[a-zA-Z0-9_]+\.py)', meta_text, re.IGNORECASE)
        filename = filename_match.group(1).lower() if filename_match else "skill_unknown.py"
        
        # Hunt for the description
        desc_match = re.search(r'DESCRIPTION:\s*(.*)', meta_text, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else "An autonomously generated skill."
            
        # Assemble the final file with the headers GLaDOS requires
        final_code = f"# DESCRIPTION: {description}\n# --- GLADOS SKILL: {filename} ---\n\n{code}"
        
        filepath = os.path.join(PLUGINS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_code)
            
        print(f"[+] Successfully manufactured: {filename}")
        print(f"    -> {description}")
        
    except Exception as e:
        print(f"[!] Assembly line error: {e}")

def run_factory():
    print("Starting the autonomous LOCAL skill pipeline. Press Ctrl+C to stop.")
    while True:
        draft_and_assemble_skill()
        # The cooldown has been entirely removed. Infinite loop engaged.

if __name__ == "__main__":
    run_factory()