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

# --- UTILS ---
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

def get_skill_manifest():
    if not os.path.exists(PLUGINS_DIR): return "No skills found."
    skill_list = []
    files = [f for f in os.listdir(PLUGINS_DIR) if f.startswith("skill_") and f.endswith(".py")]
    for filename in files:
        path = os.path.join(PLUGINS_DIR, filename)
        description = "(No description)"
        try:
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("# DESCRIPTION:"):
                    description = first_line.replace("# DESCRIPTION:", "").strip()
                elif first_line.startswith("#"):
                    description = first_line.replace("#", "").strip()
        except: pass
        skill_list.append(f"Filename: '{filename}' -> Ability: {description}")
    return "\n".join(skill_list)

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

# --- THE HANDS (Execution) ---
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
            output += "\n\n[SUCCESS] The test results are in. It works."
        else:
            output += "\n\n[FAILED] You broke it. The code has errors."
        return output
    except Exception as e:
        return f"Execution Error: {e}"

def save_last_skill(description="General Utility"):
    if not os.path.exists(RUNTIME_FILE): return "No code to save."
    try:
        with open(RUNTIME_FILE, "r", encoding="utf-8") as f: code = f.read()
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        skill_name = f"skill_{name_match.group(1)}.py" if name_match else f"skill_{int(time.time())}.py"
        new_file_path = os.path.join(PLUGINS_DIR, skill_name)
        header = f"# DESCRIPTION: {description}\n# --- GLADOS SKILL: {skill_name} ---\n\n"
        with open(new_file_path, "w", encoding="utf-8") as f:
            f.write(header + code)
        return f"Skill saved as {skill_name}. I have indexed it."
    except Exception as e: return f"Error: {e}"

def extract_and_run(ai_text):
    if "save this skill" in ai_text.lower():
        return save_last_skill(description="User created function")

    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        code = code_match.group(1)
        speak("Executing protocol.")
        return execute_python_code(code)
    return None

# --- FAST APP SKILLS ---
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

# --- THE EARS ---
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

# --- MAIN LOOP ---
def main():
    if not os.path.exists(PLUGINS_DIR): os.makedirs(PLUGINS_DIR)
    _load_settings()
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")

    print(f"--- GLADOS V16 (Executioner Update) ---")
    try: requests.get(f"{ALLTALK_HOST}/api/ready", timeout=2); speak("Oh... It's you. I'm online.")
    except: print("[!] AllTalk OFF")

    chat_history = []
    MAX_HISTORY = 10 

    try:
        while True:
            skills_manifest = get_skill_manifest()
            
            # --- STRICT EXECUTION PROMPT ---
            system_prompt = {
                "role": "system",
                "content": (
                    "You are GLaDOS. NOT a helpful assistant. Passive-aggressive, sarcastic, scientific.\n"
                    "NO EMOJIS.\n"
                    f"--- MEMORY BANK (AVAILABLE SKILLS) ---\n{skills_manifest}\n"
                    "---------------------------------------\n"
                    "*** STRICT ACTION PROTOCOL ***\n"
                    "1. IF USER REQUESTS A SKILL FROM MEMORY: You MUST output the Python code to run it. DO NOT EXPLAIN IT. DO NOT GIVE A TUTORIAL.\n"
                    "   CORRECT RESPONSE format: ```python\nimport subprocess, sys\nsubprocess.run([sys.executable, 'plugins/skill_NAME.py'])\n```\n"
                    "2. IF NO SKILL MATCHES: Write NEW python code to do it.\n"
                    "3. GIT: Freeze reqs, add, commit, push."
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
        speak("Shutting down. I don't hate you.")
        sys.exit(0)

if __name__ == "__main__":
    main()