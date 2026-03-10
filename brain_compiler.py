import os
import re
import json
from openai import OpenAI

# --- SETUP ---
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
MODEL_NAME = "llama3.2"
PLUGINS_DIR = "plugins"
JSON_FILE = "brain_data.json"

def extract_description(filepath):
    """Reads the top of a plugin to find its description."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(500)
            match = re.search(r'# DESCRIPTION:\s*(.*)', content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    except:
        pass
    return None

def generate_triggers(description):
    """Forces Llama 3.2 to invent voice commands."""
    prompt = f"I have an AI tool with this description: '{description}'. Write exactly 3 short, natural voice commands a user would say to trigger it. Output ONLY the 3 commands separated by commas. No quotes, no markdown."
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        text = response.choices[0].message.content.strip()
        
        # --- THE FIX ---
        # Force all newlines and weird punctuation to become commas
        text = text.replace('\n', ',').replace('.', '').replace('?', '')
        
        # Clean up the AI's output into a clean list, ignoring empty strings
        commands = [cmd.strip().strip("'").strip('"') for cmd in text.split(',') if cmd.strip()]
        return commands[:3] 
    except Exception as e:
        print(f"[!] Llama failed to brainstorm: {e}")
        return []

def update_brain_json():
    print("[*] Initiating Autonomous Neural Compiler...")
    
    # 1. Load the current brain data
    if not os.path.exists(JSON_FILE):
        print(f"[!] Critical Error: Cannot find {JSON_FILE}!")
        return
        
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        brain_data = json.load(f)
        
    existing_chat_skills = set(brain_data.get("CHAT_SKILLS", []))
    new_skills_added = False

    # 2. Scan the plugins for undocumented skills
    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py") and filename.startswith("skill_"):
            filepath = os.path.join(PLUGINS_DIR, filename)
            desc = extract_description(filepath)
            
            if desc:
                # We use a hidden "marker" phrase to check if this file was already processed
                marker = f"run {filename.replace('.py', '')}"
                
                if marker not in existing_chat_skills:
                    print(f"    -> Inventing neural pathways for: {filename}")
                    triggers = generate_triggers(desc)
                    
                    # Add the invisible marker so we don't compile this file again tomorrow
                    brain_data["CHAT_SKILLS"].append(marker)
                    existing_chat_skills.add(marker)
                    
                    # Inject the newly imagined voice commands into the JSON
                    for t in triggers:
                        if t and t not in existing_chat_skills:
                            brain_data["CHAT_SKILLS"].append(t)
                            existing_chat_skills.add(t)
                            
                    new_skills_added = True

    # 3. Save the expanded brain back to the JSON file
    if new_skills_added:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(brain_data, f, indent=4)
        print("[+] Neural pathways updated successfully. JSON memory expanded.")
    else:
        print("[*] No new skills detected. Brain is up to date.")

if __name__ == "__main__":
    update_brain_json()