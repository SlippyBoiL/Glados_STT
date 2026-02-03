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

# XTTS GENERATION SETTINGS
XTTS_SETTINGS = {
    "temperature": 0.75,
    "top_k": 50,
    "top_p": 0.85,
    "repetition_penalty": 1.2,
    "language": "en"
}

PLUGINS_DIR = "plugins"
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")

# --- WAKE WORDS ---
WAKE_WORDS = ["hey glados", "glados", "okay glados", "hi glados", "hey glass", "hey gladys"]

# --- APP DATABASE ---
APP_ALIASES = {
    "chrome": "chrome", "google chrome": "chrome", "firefox": "firefox", "edge": "msedge",
    "notepad": "notepad", "calculator": "calc", "calc": "calc", "explorer": "explorer",
    "cmd": "cmd", "discord": "discord", "spotify": "spotify", "steam": "steam",
    "vs code": "code", "code": "code"
}

# --- TECHNICAL AUTOCORRECT ---
TECHNICAL_FIXES = {
    "colonel": "kernel", "kernel.py": "kernel.py", "pseudo": "sudo",
    "get": "git", "hub": "hub", "deaf": "def", "sink": "sync",
    "pushed": "push", "requirments": "requirements", "recipie": "receipt"
}

# --- SAFETY ---
DENYLIST_PATTERNS = [r"\bformat\s+[a-z]:\b", r"kernel\.py", r"del\s+.*kernel\.py"]

client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

# --- AUDIO SETTINGS ---
VOICE_VOLUME = 1.0       
PLAYBACK_SPEED = 1.0    

try:
    from autocorrect import Speller
    spell = Speller(lang='en')
    SPELL_CHECK_ACTIVE = True
except ImportError:
    SPELL_CHECK_ACTIVE = False

# ==================================================================================
# --- CLASS: SKILL MANAGER (THE V18 BRAIN - UNTOUCHED) ---
# ==================================================================================
class SkillManager:
    def __init__(self, plugins_dir):
        self.plugins_dir = plugins_dir
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            
    def get_manifest(self):
        """Scans the folder and returns a formatted string for the AI prompt."""
        skills = []
        files = [f for f in os.listdir(self.plugins_dir) if f.startswith("skill_") and f.endswith(".py")]
        
        print(f"\n[DEBUG] Scanning Memory... Found {len(files)} skills.")
        
        for filename in files:
            path = os.path.join(self.plugins_dir, filename)
            description = "No description provided."
            try:
                with open(path, "r", encoding="utf-8") as f:
                    # Read first 3 lines to find a description
                    for _ in range(3):
                        line = f.readline().strip()
                        if line.startswith("# DESCRIPTION:"):
                            description = line.replace("# DESCRIPTION:", "").strip()
                            break
                        elif line.startswith("#") and "GLADOS SKILL" not in line:
                            description = line.replace("#", "").strip()
            except: pass
            
            skills.append(f"- FILE: '{filename}' | ACTION: {description}")
            print(f"   -> Loaded: {filename} ({description})")
            
        if not skills:
            return "NO SKILLS FOUND. You have no long-term memory yet."
            
        return "\n".join(skills)

    def save_skill(self, code, description="General Utility"):
        """Saves code to a new named file."""
        # Extract function name for filename
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        if name_match:
            skill_name = f"skill_{name_match.group(1)}.py"
        else:
            skill_name = f"skill_{int(time.time())}.py"
            
        path = os.path.join(self.plugins_dir, skill_name)
        
        # Header for better indexing
        header = f"# DESCRIPTION: {description}\n# --- GLADOS SKILL: {skill_name} ---\n\n"
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + code)
            return skill_name
        except Exception as e:
            print(f"[!] Save Error: {e}")
            return None

# Initialize Manager
skill_brain = SkillManager(PLUGINS_DIR)

# ==================================================================================
# --- UTILITIES ---
# ==================================================================================
def clean_text_for_speech(text):
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    text = text.replace("\\", "")
    return text.strip()

def correct_input_text(text):
    if not text: return ""
    words = text.split()
    fixed_words = []
    for w in words:
        clean_w = w.lower().strip(".,?!")
        if clean_w in TECHNICAL_FIXES: fixed_words.append(TECHNICAL_FIXES[clean_w])
        else: fixed_words.append(w)
    text = " ".join(fixed_words)
    if SPELL_CHECK_ACTIVE and "def " not in text: text = spell(text)
    return text

def is_wake_word(text):
    text_lower = text.lower()
    for trigger in WAKE_WORDS:
        if text_lower.startswith(trigger):
            return trigger, text[len(trigger):].strip()
        ratio = SequenceMatcher(None, trigger, text_lower[:len(trigger)+5]).ratio()
        if ratio > 0.75:
            return trigger, text_lower.replace(text_lower[:len(trigger)], "").strip()
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

def check_voice_availability():
    try:
        requests.get(f"{ALLTALK_HOST}/api/ready", timeout=2)
    except Exception as e:
        print(f"[!] WARNING: AllTalk disconnected at {ALLTALK_HOST}")

def speak(text):
    clean_text = clean_text_for_speech(text)
    print(f"\nGLADOS: {clean_text}")
    print("[*] Generating audio...")
    
    payload = {
        "text_input": clean_text,
        "character_voice_gen": VOICE_NAME,
        "text_filtering": "standard",
        **XTTS_SETTINGS
    }

    try:
        response = requests.post(f"{ALLTALK_HOST}/api/tts-generate", data=payload, timeout=60)
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

# ==================================================================================
# --- THE HANDS (EXECUTION) ---
# ==================================================================================
def execute_python_code(code_block):
    if "kernel.py" in code_block and ("write" in code_block or "delete" in code_block):
        return "ERROR: ACCESS DENIED. You cannot modify kernel.py."

    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        f.write(code_block)
    
    print(f"[*] EXECUTING RUNTIME...")
    try:
        result = subprocess.run([sys.executable, RUNTIME_FILE], capture_output=True, text=True, timeout=45)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            output += "\n\n[SUCCESS]"
        else:
            output += "\n\n[FAILED]"
        return output
    except Exception as e:
        return f"Execution Error: {e}"

def extract_and_run(ai_text):
    # Check for SAVE command
    if "save this skill" in ai_text.lower():
        # Read the last runtime code
        if not os.path.exists(RUNTIME_FILE): return "No code to save."
        with open(RUNTIME_FILE, "r", encoding="utf-8") as f: code = f.read()
        
        saved_name = skill_brain.save_skill(code, description="User defined skill")
        if saved_name:
            speak("Archived.")
            return f"Saved as {saved_name}. Added to Memory Bank."
        else:
            return "Error saving skill."

    # Check for EXECUTE command
    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        code = code_match.group(1)
        speak("Running.")
        return execute_python_code(code)
    return None

# ==================================================================================
# --- FAST APP SKILLS ---
# ==================================================================================
def handle_app_open(text):
    text = text.lower()
    if not any(k in text for k in ["open", "start", "launch"]): return False
    app_name = text.replace("open", "").replace("start", "").replace("launch", "").strip()
    exe_name = APP_ALIASES.get(app_name, app_name)
    try:
        os.system(f"start {exe_name}") 
        speak(f"Starting {app_name}.")
        return True
    except: return False

def handle_app_close(text):
    text = text.lower()
    if not any(k in text for k in ["close", "quit", "terminate"]): return False
    app_name = text.replace("close", "").replace("quit", "").strip()
    exe_name = APP_ALIASES.get(app_name, app_name)
    if not exe_name.endswith(".exe"): exe_name += ".exe"
    try:
        os.system(f"taskkill /f /im {exe_name}")
        speak(f"Terminating {app_name}.")
        return True
    except: return False

# ==================================================================================
# --- THE EARS ---
# ==================================================================================
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
                trigger_found, command_part = is_wake_word(raw_text)
                
                if trigger_found:
                    print(f"[!] WAKE WORD: '{trigger_found}'")
                    if not command_part or len(command_part) < 2:
                        print("Listening for command...")
                        try:
                            audio_cmd = r.listen(source, timeout=8) 
                            command_part = r.recognize_google(audio_cmd)
                        except: continue
                    
                    final_command = correct_input_text(command_part)
                    print(f"YOU: {final_command}")
                    return final_command
            except: pass

# ==================================================================================
# --- MAIN LOOP ---
# ==================================================================================
def main():
    _load_settings()
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")

    print(f"--- GLADOS V18 (Quiet Edition) ---")
    check_voice_availability()
    speak("Online.")

    chat_history = []
    MAX_HISTORY = 6 

    try:
        while True:
            # 1. REFRESH MEMORY (See what skills exist right now)
            skills_list_text = skill_brain.get_manifest()
            
            # 2. CONSTRUCT PROMPT (UPDATED FOR SILENCE)
            system_prompt = {
                "role": "system",
                "content": (
                    "You are GLaDOS. NOT a helpful assistant.\n"
                    "PERSONALITY: Cold, efficient, concise (Max 1 sentence).\n"
                    "NO EMOJIS.\n"
                    "*** STRICT ACTION PROTOCOL ***\n"
                    "1. SEARCH MEMORY BANK BELOW. If the user asks for a skill listed there, RUN IT.\n"
                    "   DO NOT EXPLAIN STEPS. DO NOT SAY 'HERE IS THE CODE'. JUST THE CODE.\n"
                    "   RUN IT by outputting: ```python\nimport subprocess, sys\nsubprocess.run([sys.executable, 'plugins/skill_NAME.py'])\n```\n"
                    "2. If NOT in memory, write NEW python code. NO EXPLANATION.\n"
                    "3. GIT: Freeze reqs, add, commit, push.\n"
                    "\n"
                    "---------------------------------------\n"
                    "*** MEMORY BANK (AVAILABLE SKILLS) ***\n"
                    f"{skills_list_text}\n"
                    "---------------------------------------"
                )
            }

            messages = [system_prompt] + chat_history

            user_input = listen()
            if not user_input: continue
            if "exit" in user_input.lower(): raise KeyboardInterrupt
            
            if handle_app_open(user_input): continue
            if handle_app_close(user_input): continue
            
            messages.append({"role": "user", "content": user_input})
            chat_history.append({"role": "user", "content": user_input})

            try:
                print("[*] Thinking...")
                response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
                ai_text = response.choices[0].message.content
                
                chat_history.append({"role": "assistant", "content": ai_text})
                if len(chat_history) > MAX_HISTORY: chat_history = chat_history[-MAX_HISTORY:]
                
                execution_result = extract_and_run(ai_text)
                
                if execution_result:
                    chat_history.append({"role": "user", "content": f"SYSTEM OUTPUT: {execution_result}"})
                    final_res = client.chat.completions.create(model=MODEL_NAME, messages=messages)
                    speak(final_res.choices[0].message.content) 
                    chat_history.append({"role": "assistant", "content": final_res.choices[0].message.content})
                else:
                    speak(ai_text)
            except Exception as e:
                print(f"[!] ERROR: {e}")

    except KeyboardInterrupt:
        print("\n[!] FORCE QUIT.")
        speak("Shutting down.")
        sys.exit(0)

if __name__ == "__main__":
    main()