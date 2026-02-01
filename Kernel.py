import os
import re
import subprocess
import sys
import time
import json
import requests
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
import io
from difflib import SequenceMatcher
from openai import OpenAI

# --- CONFIGURATION ---
PERPLEXITY_API_KEY = "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"
MODEL_NAME = "sonar-pro"

# TTS SETTINGS
ALLTALK_HOST = "http://127.0.0.1:7851"
VOICE_NAME = "frieren.wav" 

PLUGINS_DIR = "plugins"
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SHARED_FILE = os.path.join(PLUGINS_DIR, "my_skills.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")

# --- WAKE WORDS (Fuzzy Matched) ---
WAKE_WORDS = ["hey glados", "glados", "okay glados", "hi glados", "hey glass", "hey gladys"]

# --- TECHNICAL AUTOCORRECT ---
# Fixes common voice-to-text coding errors
TECHNICAL_FIXES = {
    "colonel": "kernel",
    "kernel.py": "kernel.py", # Protects filename
    "pseudo": "sudo",
    "get": "git",
    "hub": "hub",
    "deaf": "def",
    "star": "str",
    "ant": "int",
    "bowl": "bool",
    "variable": "var",
    "sink": "sync",
    "pushed": "push",
    "commit": "commit",
    "requirments": "requirements",
    "recipie": "receipt"
}

# --- SAFETY ---
ALLOWED_PATH_ROOTS = [r"C:\\"]
DENYLIST_PATTERNS = [
    r"\bformat\s+[a-z]:\b", r"\bshutdown\s*/[sr]\b", r"System32",
    r"kernel\.py", r"del\s+.*kernel\.py"
]

client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

# --- AUDIO SETTINGS ---
VOICE_VOLUME = 1.0       
PLAYBACK_SPEED = 1.15    

# --- SPELL CHECKER LOADER ---
try:
    from autocorrect import Speller
    spell = Speller(lang='en')
    SPELL_CHECK_ACTIVE = True
except ImportError:
    SPELL_CHECK_ACTIVE = False
    print("[!] Tip: Run 'pip install autocorrect' for better spelling fixes.")

def clean_text_for_speech(text):
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    text = text.replace("\\", "")
    text = re.sub(r"\b[a-zA-Z]:\\[^\s'\"`]+", "file path", text)
    text = text.replace("**", "").replace("###", "")
    return text.strip()

def correct_input_text(text):
    """
    Applies technical fixes and spell checking to user input.
    """
    if not text: return ""
    
    # 1. Technical Dictionary Replacement
    words = text.split()
    fixed_words = []
    for w in words:
        clean_w = w.lower().strip(".,?!")
        # Replace if in dictionary
        if clean_w in TECHNICAL_FIXES:
            fixed_words.append(TECHNICAL_FIXES[clean_w])
        else:
            fixed_words.append(w)
    
    text = " ".join(fixed_words)

    # 2. General Spell Check (if installed)
    # We skip spell checking for code-heavy lines to avoid breaking variable names
    if SPELL_CHECK_ACTIVE and "def " not in text and "import " not in text:
        text = spell(text)
        
    return text

def is_wake_word(text):
    """
    Fuzzy matches the wake word. 
    Allows 'Hey Gladys' to trigger 'Hey Glados'.
    """
    text_lower = text.lower()
    for trigger in WAKE_WORDS:
        # Check exact match start
        if text_lower.startswith(trigger):
            return trigger, text[len(trigger):].strip()
            
        # Check fuzzy match (Similarity > 0.8)
        # We check the first few words against the trigger
        trigger_len = len(trigger)
        snippet = text_lower[:trigger_len + 5] # Taking a safe slice
        
        ratio = SequenceMatcher(None, trigger, snippet).ratio()
        if ratio > 0.75: # 75% match allowed
            return trigger, text_lower.replace(snippet, "").strip()
            
    return None, None

def _load_settings():
    global VOICE_VOLUME
    if not os.path.exists(SETTINGS_PATH): return
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vol = float(data.get("voice_volume", VOICE_VOLUME))
        VOICE_VOLUME = max(0.1, min(1.5, vol))
    except: pass

def _save_settings():
    try:
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"voice_volume": VOICE_VOLUME}, f)
    except: pass

# --- THE MOUTH ---
def speak(text):
    clean_text = clean_text_for_speech(text)
    print(f"\nGLADOS: {clean_text}")
    print("[*] Generating audio...")

    try:
        response = requests.post(
            f"{ALLTALK_HOST}/api/tts-generate",
            data={"text_input": clean_text, "character_voice_gen": VOICE_NAME, "language": "en"},
            timeout=60,
        )
        if response.status_code == 200:
            try:
                receipt = response.json()
                if receipt.get("status") == "generate-success":
                    audio_path = receipt.get("output_file_url")
                    download_url = f"{ALLTALK_HOST}{audio_path}"
                    audio_response = requests.get(download_url)
                    audio_data = io.BytesIO(audio_response.content)
                    data, samplerate = sf.read(audio_data)
                    try:
                        scaled = data * VOICE_VOLUME
                        if hasattr(scaled, "clip"): scaled = scaled.clip(-1.0, 1.0)
                        sd.play(scaled, int(samplerate * PLAYBACK_SPEED))
                    except:
                        sd.play(data, int(samplerate * PLAYBACK_SPEED))
                    sd.wait() 
                    time.sleep(0.5) 
            except: pass
    except Exception as e:
        print(f"[!] AUDIO FAILED: {e}")

# --- THE HANDS ---
def execute_python_code(code_block):
    if "kernel.py" in code_block and ("write" in code_block or "delete" in code_block):
        return "ERROR: ACCESS DENIED. You cannot modify kernel.py."

    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        f.write(code_block)
    
    print(f"[*] TESTING CODE...")
    try:
        result = subprocess.run([sys.executable, RUNTIME_FILE], capture_output=True, text=True, timeout=45)
        output = result.stdout + result.stderr
        
        if result.returncode == 0:
            output += "\n\n[SUCCESS] Code executed. Say 'Save this skill' to keep it."
        else:
            output += "\n\n[FAILED] Code errors."
        return output
    except Exception as e:
        return f"Execution Error: {e}"

def save_last_skill():
    if not os.path.exists(RUNTIME_FILE): return "No code to save."
    try:
        with open(RUNTIME_FILE, "r", encoding="utf-8") as f: code = f.read()
        
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        if name_match:
            skill_name = f"skill_{name_match.group(1)}.py"
        else:
            skill_name = f"skill_{int(time.time())}.py"

        new_file_path = os.path.join(PLUGINS_DIR, skill_name)
        
        with open(new_file_path, "w", encoding="utf-8") as f:
            f.write(f"# --- GLADOS SKILL: {skill_name} ---\n\n{code}")
            
        return f"Skill saved as {skill_name}."
    except Exception as e: return f"Error: {e}"

def extract_and_run(ai_text):
    if "save this skill" in ai_text.lower():
        speak("Saving skill.")
        return save_last_skill()

    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        code = code_match.group(1)
        speak("Running protocol.")
        return execute_python_code(code)
    return None

# --- THE EARS (Fuzzy Wake Word) ---
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\nWaiting for 'Hey Glados'...")
        r.adjust_for_ambient_noise(source, duration=2.0)
        r.dynamic_energy_threshold = True 
        r.pause_threshold = 2.0 

        while True:
            try:
                audio = r.listen(source, timeout=None)
                raw_text = r.recognize_google(audio)
                
                # Check Wake Word (Fuzzy)
                trigger_found, command_part = is_wake_word(raw_text)
                
                if trigger_found:
                    print(f"[!] WAKE WORD DETECTED: '{trigger_found}' (from '{raw_text}')")
                    
                    # If no command followed (e.g., just "Hey Glados"), listen again
                    if not command_part or len(command_part) < 2:
                        print("Listening for command...")
                        try:
                            audio_cmd = r.listen(source, timeout=8) 
                            command_part = r.recognize_google(audio_cmd)
                        except:
                            print("(Timeout waiting for command)")
                            continue
                    
                    # Apply Autocorrect to the command
                    final_command = correct_input_text(command_part)
                    print(f"YOU: {final_command}")
                    return final_command
                
                print(f"(Ignored: {raw_text})")
            except: pass

# --- MAIN LOOP ---
def main():
    if not os.path.exists(PLUGINS_DIR): os.makedirs(PLUGINS_DIR)
    if not os.path.exists(SHARED_FILE):
        with open(SHARED_FILE, "w") as f: f.write("# Shared Utilities\n")
    _load_settings()
    
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")

    messages = [{
        "role": "system",
        "content": (
            "You are GLADOS. Conversational, Professional, Admin Access.\n"
            "NO EMOJIS.\n"
            "TASKS: Write Python code in ```python``` blocks.\n"
            "GIT PUSH: If asked to push/sync:\n"
            "   1. Write code to run `pip freeze > requirements.txt`.\n"
            "   2. Run `git add .`\n"
            "   3. Run `git commit -m 'Auto-Sync'`\n"
            "   4. Run `git push origin main`"
        )
    }]

    print(f"--- GLADOS V8 (Autocorrect Online) ---")
    try: requests.get(f"{ALLTALK_HOST}/api/ready", timeout=2); speak("Online.")
    except: print("[!] AllTalk OFF")

    while True:
        user_input = listen()
        if not user_input: continue
        if "exit" in user_input.lower(): break
        
        messages.append({"role": "user", "content": user_input})

        try:
            print("[*] Thinking...")
            response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
            ai_text = response.choices[0].message.content
            
            execution_result = extract_and_run(ai_text)
            
            if execution_result:
                messages.append({"role": "assistant", "content": ai_text})
                messages.append({"role": "user", "content": f"OUTPUT:\n{execution_result}"})
                final_res = client.chat.completions.create(model=MODEL_NAME, messages=messages)
                speak(final_res.choices[0].message.content) 
                messages.append({"role": "assistant", "content": final_res.choices[0].message.content})
            else:
                speak(ai_text)
                messages.append({"role": "assistant", "content": ai_text})
                
        except Exception as e:
            print(f"[!] ERROR: {e}")

if __name__ == "__main__":
    main()