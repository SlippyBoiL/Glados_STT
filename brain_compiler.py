import os
import re
from openai import OpenAI

# --- SETUP ---
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
MODEL_NAME = "llama3.2"
PLUGINS_DIR = "Plugins"

# --- CORE INTENTS (The foundation of the brain) ---
BASE_LIGHTS = [
    "turn on the bedroom lights", "make the tv red", "lights off", "dim the closet to 50%", 
    "turn the strip blue", "illuminate the room", "shut off the lights", "brightness to 100", 
    "set lights to warm", "pitch black", "give me some light", "it is too dark in here", 
    "govee lights on", "change the bedroom to purple"
]
BASE_OPEN = [
    "open google chrome", "start discord", "launch steam", "boot up vs code", "open calculator", 
    "fire up the browser", "start my game client", "open up spotify", "launch edge", "run notepad"
]
BASE_CLOSE = [
    "kill steam", "close notepad", "terminate discord", "shut down chrome", "quit edge", 
    "destroy spotify", "force quit calculator", "stop the browser", "exit vs code", "close everything"
]
BASE_CHAT = [
    "hello glados", "write a python script for me", "what is the meaning of life", 
    "you are terrible", "save this skill", "how do i bake a cake", "what is the weather", 
    "tell me a joke", "you are a useless machine", "run the diagnostic"
]

def extract_description(filepath):
    """Reads the first few lines of a plugin to find its description."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(500) # Only read the top chunk
            match = re.search(r'# DESCRIPTION:\s*(.*)', content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    except:
        pass
    return None

def generate_triggers(description):
    """Forces Llama 3.2 to invent 3 voice commands for a given description."""
    prompt = f"I have an AI tool with this description: '{description}'. Write exactly 3 short, natural voice commands a user would say to trigger it. Output ONLY the 3 commands separated by commas. No quotes, no bullet points, no markdown, no extra text."
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3 # Low temperature to keep it strict and robotic
        )
        text = response.choices[0].message.content.strip()
        # Clean up the AI's output into a clean list
        commands = [cmd.strip().strip("'").strip('"') for cmd in text.split(',')]
        return commands[:3] # Ensure we only grab 3
    except Exception as e:
        print(f"[!] Llama failed to generate triggers: {e}")
        return [f"run the {description[:10]} skill"]

def compile_brain():
    print("[*] Sweeping Memory Bank for installed plugins...")
    skill_triggers = []
    
    if not os.path.exists(PLUGINS_DIR):
        print(f"[!] Error: Could not find {PLUGINS_DIR} folder.")
        return

    # 1. Read the plugins
    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py"):
            filepath = os.path.join(PLUGINS_DIR, filename)
            desc = extract_description(filepath)
            if desc:
                print(f"    -> Analyzing {filename}...")
                triggers = generate_triggers(desc)
                skill_triggers.extend(triggers)
                
    print("\n[*] Compiling Neural Arrays...")
    
    # 2. Combine the base foundation with the newly imagined skill triggers
    all_sentences = BASE_LIGHTS + BASE_OPEN + BASE_CLOSE + BASE_CHAT + skill_triggers
    
    # 3. Mathematically map out the labels to match the lengths perfectly
    labels = []
    labels.extend([0] * len(BASE_LIGHTS))
    labels.extend([1] * len(BASE_OPEN))
    labels.extend([2] * len(BASE_CLOSE))
    labels.extend([3] * (len(BASE_CHAT) + len(skill_triggers)))
    
    # 4. Print the final code for the user
    print("\n" + "="*80)
    print("COPY AND PASTE EVERYTHING BELOW THIS LINE INTO omni_brain.py")
    print("="*80 + "\n")
    
    print("training_sentences = [")
    for i, sentence in enumerate(all_sentences):
        # Formatting to add commas everywhere except the very last item
        comma = "," if i < len(all_sentences) - 1 else ""
        print(f'    "{sentence}"{comma}')
    print("]\n")
    
    # Format the labels array cleanly
    labels_str = ", ".join(map(str, labels))
    print(f"training_labels = np.array([\n    {labels_str}\n])")
    print("\n" + "="*80)

if __name__ == "__main__":
    compile_brain()