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
from openai import OpenAI

# --- CONFIGURATION ---
PERPLEXITY_API_KEY = "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"
MODEL_NAME = "sonar-pro"

# TTS SETTINGS
ALLTALK_HOST = "http://127.0.0.1:7851"
VOICE_NAME = "frieren.wav" 

PLUGINS_DIR = "plugins"
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SKILLS_FILE = os.path.join(PLUGINS_DIR, "my_skills.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")

# --- WAKE WORDS ---
WAKE_WORDS = ["hey glados", "glados", "okay glados", "hi glados"]

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

def clean_text_for_speech(text):
    # 1. Strip Code Blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    
    # 2. Strip Citations
    text = re.sub(r"\[\d+\]", "", text)
    
    # 3. Strip Emojis (Range check for high unicode)
    # This regex removes characters typically used for emojis
    text = re.sub(r"[^\x00-\x7F]+", "", text) 
    
    # 4. Strip Paths and Markdown
    text = text.replace("\\", "")
    text = re.sub(r"\b[a-zA-Z]:\\[^\s'\"`]+", "file path", text)
    text = text.replace("**", "").replace("###", "")
    
    return text.strip()

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
        with open(SKILLS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n\n# --- NEW SKILL {time.ctime()} ---\n{code}\n")
        return "Skill saved to memory."
    except Exception as e: return f"Error: {e}"

def extract_and_run(ai_text):
    if "save this skill" in ai_text.lower():
        speak("Saving to memory.")
        return save_last_skill()

    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        code = code_match.group(1)
        speak("Running protocol.")
        return execute_python_code(code)
    return None

# --- THE EARS (Wake Word Logic) ---
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\nWaiting for 'Hey Glados'...")
        r.adjust_for_ambient_noise(source, duration=1.0)
        r.pause_threshold = 1.0 

        while True:
            try:
                # Short listen loop to check for wake word
                audio = r.listen(source, timeout=None, phrase_time_limit=10)
                text = r.recognize_google(audio).lower()
                
                # CHECK: Does it start with a wake word?
                activated = False
                for trigger in WAKE_WORDS:
                    if text.startswith(trigger):
                        print(f"[!] WAKE WORD DETECTED: '{trigger}'")
                        # Strip the wake word to get the actual command
                        command = text.replace(trigger, "").strip()
                        
                        # If user just said "Hey Glados" and stopped, listen again for command
                        if not command:
                            print("Listening for command...")
                            audio_cmd = r.listen(source, timeout=5)
                            command = r.recognize_google(audio_cmd)
                            
                        print(f"YOU: {command}")
                        return command
                
                print(f"(Ignored: {text})")
                
            except sr.WaitTimeoutError: pass
            except sr.UnknownValueError: pass
            except Exception as e: print(f"Error: {e}")

# --- MAIN LOOP ---
def main():
    if not os.path.exists(PLUGINS_DIR): os.makedirs(PLUGINS_DIR)
    if not os.path.exists(SKILLS_FILE):
        with open(SKILLS_FILE, "w") as f: f.write("# GLADOS SKILLS\n")
    _load_settings()

    messages = [{
        "role": "system",
        "content": (
            "You are GLADOS. A conversational, professional AI.\n"
            "STRICT RULE: NO EMOJIS. NEVER use emojis in your text.\n"
            "You have Admin access. If asked for tasks (files, git, math), WRITE PYTHON CODE.\n"
            "GIT: If asked to 'push to main project', write python code to run:\n"
            "   `git add .`\n"
            "   `git commit -m 'Voice update'`\n"
            "   `git push origin main`\n"
            "SAFETY: Do not delete kernel.py."
        )
    }]

    print(f"--- GLADOS V5 (Wake Word: 'Hey Glados') ---")
    try: requests.get(f"{ALLTALK_HOST}/api/ready", timeout=2); speak("Online. Waiting for wake word.")
    except: print("[!] AllTalk OFF")

    while True:
        # Loop waits inside listen() until "Hey Glados" is heard
        user_input = listen()
        
        if not user_input: continue
        if "exit" in user_input.lower(): break
        
        # Git Push Shortcut logic handled by system prompt instructions now, 
        # but we can enforce it here too if needed.
        
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