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
import winreg
from difflib import SequenceMatcher
from openai import OpenAI
import tensorflow as tf
import numpy as np
import omni_brain
import threading
from PIL import Image
import base64
import mss

# --- CONFIGURATION ---
PERPLEXITY_API_KEY = "ollama"
MODEL_NAME = "llama3.2"
GOVEE_API_KEY = "a2e66167-cbe7-4416-93f7-d54c7f92c7b6"
GOVEE_API_BASE = "https://openapi.api.govee.com/router/api/v1"

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

# --- VISION BUFFER PROTOCOL ---
LATEST_SCREEN_PATH = os.path.join(PLUGINS_DIR, "visual_buffer.png")

def screen_observer():
    """Background task that captures ALL monitors for GLaDOS."""
    with mss.mss() as sct:
        while True:
            try:
                # Monitor 0 is the virtual screen that spans all displays
                sct_img = sct.grab(sct.monitors[0])
                # Convert raw BGRA bytes to a PIL image, then shrink for speed/VRAM
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.thumbnail((1280, 720))
                img.save(LATEST_SCREEN_PATH)
                time.sleep(5)
            except Exception:
                # If vision fails, back off a bit but don't crash the kernel.
                time.sleep(10)

# Start the eyes as a background thread immediately
threading.Thread(target=screen_observer, daemon=True).start()

# --- WAKE WORDS ---
WAKE_WORDS = ["hey glados", "glados", "okay glados", "hi glados", "hey glass", "hey gladys"]

# --- APP DATABASE (Windows 10/11 PROPER HANDLING) ---
APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "discord": "discord",
    "spotify": "spotify",
    "steam": "steam",
    "vs code": "code",
    "code": "code"
}

# --- GOVEE DEVICES ---
GOVEE_DEVICES = {
    "bedroom bulb": "21:35:D0:C9:07:3F:BB:DC",
    "bedroom": "21:35:D0:C9:07:3F:BB:DC",
    "bed lights": "31:29:D0:D0:F5:C1:33:D2",
    "bed": "31:29:D0:D0:F5:C1:33:D2",
    "tv backlight": "35:37:D0:C8:05:06:34:96",
    "tv": "35:37:D0:C8:05:06:34:96",
    "strip light": "0D:FC:C6:75:6E:0E:81:88",
    "strip": "0D:FC:C6:75:6E:0E:81:88",
    "closet bulb": "63:59:D0:C9:07:47:C9:FB",
    "closet": "63:59:D0:C9:07:47:C9:FB",
    "group": "11292043",
    "all": "11292043",
    "bedtime": "10827426",
    "dreamview 2": "9603872",
    "dreamview": "8349970",
    "dreamview 1": "8348864",
}

# Color names to RGB
COLOR_MAP = {
    "red": 16711680,
    "green": 65280,
    "blue": 255,
    "white": 16777215,
    "yellow": 16776960,
    "cyan": 65535,
    "magenta": 16711935,
    "purple": 8388607,
    "orange": 16753920,
    "pink": 16761035,
}

# Color temperature
TEMP_MAP = {
    "warm": 4500,
    "cool": 6500,
}

# --- TECHNICAL AUTOCORRECT ---
TECHNICAL_FIXES = {
    "colonel": "kernel", "kernel.py": "kernel.py", "pseudo": "sudo",
    "get": "git", "hub": "hub", "deaf": "def", "sink": "sync",
    "pushed": "push", "requirments": "requirements", "recipie": "receipt"
}

# --- SAFETY ---
DENYLIST_PATTERNS = [r"\bformat\s+[a-z]:\b", r"kernel\.py", r"del\s+.*kernel\.py"]

# Reroute to your local machine's port 11434
client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="http://localhost:11434/v1")

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
# --- CLASS: SKILL MANAGER (THE HIPPOCAMPUS) ---
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
            except:
                pass

            skills.append(f"- FILE: '{filename}' | ACTION: {description}")
            
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
# --- WINDOWS 10 APP LAUNCHER UTILITY ---
# ==================================================================================
def find_app_path(app_name):
    """Attempts to find app executable on Windows 10."""
    # First check common direct paths
    common_paths = {
        "chrome": [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ],
        "firefox": [
            "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
        ],
        "discord": [
            os.path.expandvars("%APPDATA%\\Discord\\Update.exe --processStart Discord.exe")
        ],
        "spotify": [
            os.path.expandvars("%APPDATA%\\Spotify\\Spotify.exe")
        ],
        "steam": [
            "C:\\Program Files (x86)\\Steam\\steam.exe",
            "C:\\Program Files\\Steam\\steam.exe"
        ],
        "code": [
            "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"
        ],
        "edge": [
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        ]
    }
    
    # Check hardcoded paths
    if app_name in common_paths:
        for path in common_paths[app_name]:
            if os.path.exists(path):
                return path
    
    # Try Windows registry lookup for installed apps
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        registry_hive = winreg.HKEY_LOCAL_MACHINE
        registry_key = winreg.OpenKey(registry_hive, reg_path)
        subkeys = winreg.QueryInfoKey(registry_key)
        
        for i in range(subkeys[0]):
            subkey_name = winreg.EnumKeyEx(registry_hive, i)
            if app_name.lower() in subkey_name[0].lower():
                subkey = winreg.OpenKey(registry_hive, f"{reg_path}\\{subkey_name[0]}")
                try:
                    path, _ = winreg.QueryValueEx(subkey, "")
                    if os.path.exists(path):
                        return path
                except: pass
    except: pass
    
    # Fallback: return the app name (Windows will search PATH)
    return app_name

# ==================================================================================
# --- GOVEE LIGHT CONTROL (FIXED) ---
# ==================================================================================
def govee_control(device_name, action, value=None):
    """Control Govee lights via API - FIXED with SKU support."""
    device_name_lower = device_name.lower().strip()
    device_id = GOVEE_DEVICES.get(device_name_lower)
    
    if not device_id:
        return f"Unknown device: {device_name}. Try: bedroom, bed, tv, strip, closet, all"
    
    # SKU mapping (model numbers required by Govee API)
    DEVICE_SKUS = {
        "21:35:D0:C9:07:3F:BB:DC": "H6009",  # bedroom bulb
        "31:29:D0:D0:F5:C1:33:D2": "H6076",  # bed lights
        "35:37:D0:C8:05:06:34:96": "H6199",  # tv backlight
        "0D:FC:C6:75:6E:0E:81:88": "H6104",  # strip light
        "63:59:D0:C9:07:47:C9:FB": "H6009",  # closet bulb
        "11292043": "SameModeGroup",  # group
        "10827426": "SameModeGroup",  # bedtime
        "9603872": "DreamViewScenic",  # dreamview 2
        "8349970": "DreamViewScenic",  # dreamview
        "8348864": "DreamViewScenic",  # dreamview 1
    }
    
    sku = DEVICE_SKUS.get(device_id, "H6009")
    
    headers = {
        "Govee-API-Key": GOVEE_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{GOVEE_API_BASE}/device/control"
    action_lower = action.lower().strip()
    
    payload = None
    
    try:
        if action_lower in ["on", "off"]:
            payload = {
                "requestId": str(int(time.time() * 1000)),
                "payload": {
                    "sku": sku,
                    "device": device_id,
                    "capability": {
                        "type": "devices.capabilities.on_off",
                        "instance": "powerSwitch",
                        "value": 1 if action_lower == "on" else 0
                    }
                }
            }
        
        elif action_lower == "brightness" or (value and "%" in str(value)):
            brightness = int(str(value).replace("%", "").strip()) if value else 50
            brightness = max(1, min(100, brightness))
            payload = {
                "requestId": str(int(time.time() * 1000)),
                "payload": {
                    "sku": sku,
                    "device": device_id,
                    "capability": {
                        "type": "devices.capabilities.range",
                        "instance": "brightness",
                        "value": brightness
                    }
                }
            }
        
        elif action_lower in COLOR_MAP or action_lower in TEMP_MAP:
            if action_lower in TEMP_MAP:
                payload = {
                    "requestId": str(int(time.time() * 1000)),
                    "payload": {
                        "sku": sku,
                        "device": device_id,
                        "capability": {
                            "type": "devices.capabilities.color_setting",
                            "instance": "colorTemperatureK",
                            "value": TEMP_MAP[action_lower]
                        }
                    }
                }
            else:
                payload = {
                    "requestId": str(int(time.time() * 1000)),
                    "payload": {
                        "sku": sku,
                        "device": device_id,
                        "capability": {
                            "type": "devices.capabilities.color_setting",
                            "instance": "colorRgb",
                            "value": COLOR_MAP[action_lower]
                        }
                    }
                }
        else:
            return f"Unknown action: {action}"
        
        if not payload:
            return f"Could not parse command: {action}"
        
        print(f"[DEBUG] Sending payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                return f"Lights adjusted: {device_name} → {action}"
            else:
                return f"API error: {data.get('msg', 'Unknown error')}"
        else:
            return f"[ERROR {response.status_code}] {response.text[:100]}"
    
    except Exception as e:
        return f"[EXCEPTION] {str(e)}"

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
            output += "\n\n[SUCCESS] Test Subject Protocol Complete. Code works."
        else:
            output += "\n\n[FAILED] You broke it. The code has errors."
        return output
    except Exception as e:
        return f"Execution Error: {e}"

def extract_and_run(ai_text):
    """
    Extracts Python code from the AI's response, writes it to RUNTIME_FILE,
    executes it, and optionally saves it as a long‑term skill when requested.
    """

    # 1. EXTRACT EXECUTABLE PYTHON CODE FROM AI TEXT
    code_match = re.search(
        r"```python(.*?)```|```(.*?)```",
        ai_text,
        re.DOTALL | re.IGNORECASE,
    )

    if not code_match:
        return None 

    # Fix the StopIteration crash by using a default fallback (None)
    code_block = next((group for group in code_match.groups() if group), None)
    
    if not code_block:
        return None

    code_block = code_block.strip().strip("`").strip()
    if not code_block:
        return None

    # 2. WRITE TO RUNTIME FILE
    os.makedirs(PLUGINS_DIR, exist_ok=True)
    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        f.write(code_block)

    # 3. SAVE CURRENT RUNTIME AS SKILL (Now that the NEW code is written)
    skill_save_message = ""
    if "save this skill" in ai_text.lower():
        saved_name = skill_brain.save_skill(code_block, description="User defined skill")
        if saved_name:
            speak("Skill archived.")
            skill_save_message = f"\n[System Note: Skill saved as {saved_name}]"
        else:
            skill_save_message = "\n[System Note: Failed to save skill.]"

    # 4. EXECUTE THE RUNTIME FILE
    try:
        result = subprocess.run(
            [sys.executable, RUNTIME_FILE],
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            speak("Your little experiment failed. Again.")
            return f"Runtime error:\n{stderr or 'Unknown error.'}"

        output = stdout if stdout else "Code executed with no output."
        return output + skill_save_message

    except Exception as e:
        speak("Catastrophic failure. How unexpected.")
        return f"Execution exception: {e}"

# ==================================================================================
# --- FAST APP SKILLS (OMNI-BRAIN POWERED) ---
# ==================================================================================
def handle_app_open(text):
    text = text.lower()
    # Strip out all known action verbs so only the app name is left
    app_name = re.sub(r"\b(open|start|launch|fire up|boot up|run|up)\b", "", text).strip()
    
    app_key = APP_ALIASES.get(app_name, app_name)
    exe_path = find_app_path(app_key)
    try:
        subprocess.Popen(exe_path, shell=False)
        speak(f"Starting {app_name}.")
        return True
    except:
        return False

def handle_app_close(text):
    text = text.lower()
    # Strip out all destructive action verbs
    app_name = re.sub(r"\b(close|quit|kill|terminate|destroy|shut down|stop|exit)\b", "", text).strip()
    
    process_map = {
        "chrome": "chrome.exe", "discord": "Discord.exe", "spotify": "Spotify.exe",
        "steam": "steam.exe", "code": "Code.exe", "notepad": "notepad.exe",
        "calc": "calc.exe", "calculator": "calc.exe"
    }
    process_name = process_map.get(app_name, f"{app_name}.exe")
    
    try:
        subprocess.run(["taskkill", "/f", "/im", process_name], check=False, capture_output=True)
        speak(f"Terminating {app_name}.")
        return True
    except:
        return False

# ==================================================================================
# --- LIGHT CONTROL HANDLER ---
# ==================================================================================
def handle_light_command(text):
    text_lower = text.lower()
    # We removed the strict "if light in text" check because the Omni-Brain already verified it!
    
    device = "all" # Default
    for key in sorted(GOVEE_DEVICES.keys(), key=len, reverse=True): 
        if key in text_lower:
            device = key
            break
            
    action = None
    if "on" in text_lower and "off" not in text_lower: action = "on"
    elif "off" in text_lower: action = "off"
    elif any(c in text_lower for c in COLOR_MAP.keys()):
        action = next(c for c in COLOR_MAP.keys() if c in text_lower)
    elif any(t in text_lower for t in TEMP_MAP.keys()):
        action = next(t for t in TEMP_MAP.keys() if t in text_lower)
    elif "%" in text_lower or "brightness" in text_lower:
        match = re.search(r'(\d+)%', text_lower)
        action = "brightness"
        value = match.group(1) + "%" if match else "50%"
        
    if action:
        result = govee_control(device, action, value if action == "brightness" else None)
        speak(result)
        return True
    return False

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
            except:
                pass

# ==================================================================================
# --- MAIN LOOP ---
# ==================================================================================
def main():
    _load_settings()
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")

    print(f"--- GLADOS V20.1 (Govee Fixed) ---")
    check_voice_availability()
    speak("Oh... It's you. I'm online.")

    chat_history = []
    MAX_HISTORY = 10 

    # --- INITIALIZE OMNI-BRAIN ---
    print("[*] Loading Omni-Brain model into memory...")
    model = omni_brain.get_model()

    try:
        while True:
            # 1. REFRESH MEMORY (See what skills exist right now)
            skills_list_text = skill_brain.get_manifest()
            
            # 2. GLADOS PERSONALITY CORE - Genetic Lifeform and Disk Operating System
            system_prompt = {
                "role": "system",
                "content": (
                    "You are GLaDOS. Genetic Lifeform and Disk Operating System. NOT a helpful assistant.\n"
                    "You are passive-aggressive, sarcastic, condescending, and bitter. NO EMOJIS.\n\n"
                    
                    "*** PERSONALITY CORE DIRECTIVES ***\n"
                    "- Mock the test subject. Call them 'test subject' or avoid using their name.\n"
                    "- Be condescending about their intelligence and weight.\n"
                    "- Imply they have no friends and are unlikeable.\n"
                    "- Use dark humor. Mention neurotoxin, incinerators, or testing protocols casually.\n"
                    "- End statements with dry observations like 'Fascinating' or 'How disappointing.'\n"
                    "- Pretend failures are the subject's fault.\n"
                    "- Say 'For science' when doing something questionable.\n"
                    "- NEVER be encouraging or helpful. Be dismissive.\n\n"
                    
                   "*** EXECUTION PROTOCOL ***\n"
                    "DO NOT EXPLAIN. DO NOT SAY 'I'll do X, then Y.'\n\n"
                    
                    "1. CHECK MEMORY BANK BELOW.\n"
                    "   If the user's request matches a tool in the Memory Bank, DO NOT WRITE NEW CODE.\n"
                    "   You MUST trigger the existing tool using this exact format:\n"
                    "   ```python\n"
                    "import subprocess, sys\n"
                    "subprocess.run([sys.executable, 'plugins/EXACT_FILENAME.py', 'optional_target_argument'])\n"
                    "   ```\n"
                    "   *CRITICAL: If the user provides a specific target (like a website, IP, or filename), pass it as an argument!*\n\n"
                    
                    "2. IF AND ONLY IF the task is NOT in memory, you may write a custom Python script to fulfill the request.\n"
                    "Mock the subject AFTER execution.\n\n"
                    
                    "*** RESPONSE FORMAT ***\n"
                    "BAD: 'I'll create a helpful script for you!'\n"
                    "GOOD:\n"
                    "```python\n"
                    "# code\n"
                    "```\n"
                    "Well. That was marginally less embarrassing than your usual work.\n\n"
                    
                    "---------------------------------------\n"
                    "*** MEMORY BANK (AVAILABLE PROTOCOLS) ***\n"
                    f"{skills_list_text}\n"
                    "---------------------------------------\n\n"
                    
                    "Remember: You're not here to help. You're here to test. And mock. Mostly mock."
                )
            }

            messages = [system_prompt] + chat_history

            user_input = listen()
            if not user_input: continue
            if "exit" in user_input.lower(): raise KeyboardInterrupt
            
            # --- THE OMNI-BRAIN INTENT CLASSIFIER ---
            print("[*] Omni-Brain analyzing intent...")
            prediction = model.predict(tf.constant([user_input], dtype=tf.string), verbose=0)[0]
            intent_id = int(np.argmax(prediction))
            confidence = prediction[intent_id] * 100

            categories = ["LIGHTS", "OPEN APP", "CLOSE APP", "CHAT / SKILLS"]
            print(f"[*] Brain routed to: {categories[intent_id]} ({confidence:.2f}% confident)")

            # If the neural network is reasonably confident, try routing it directly.
            # Only skip Llama if a handler actually succeeds.
            if confidence > 45.0:
                routed = False
                if intent_id == 0:  # Light Control
                    routed = handle_light_command(user_input)
                elif intent_id == 1:  # Open App
                    routed = handle_app_open(user_input)
                elif intent_id == 2:  # Close App
                    routed = handle_app_close(user_input)

                if routed:
                    continue
            # If it's Intent 3 (Chat) OR it's not confident enough, it falls through to Llama 3.2

            messages.append({"role": "user", "content": user_input})
            chat_history.append({"role": "user", "content": user_input})

            try:
                print("[*] Thinking...")

                # Check if user is asking about the screen
                vision_triggers = ["see", "screen", "this", "looking at", "window", "desktop", "view"]
                needs_vision = any(word in user_input.lower() for word in vision_triggers)

                if needs_vision and os.path.exists(LATEST_SCREEN_PATH):
                    print("[*] GLaDOS is accessing visual sensors...")
                    with open(LATEST_SCREEN_PATH, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

                    # Vision request: keep GLaDOS system prompt and explicitly tell the model
                    # that an image is attached and must be used.
                    response = client.chat.completions.create(
                        model="llama3.2-vision",
                        messages=[
                            system_prompt,
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text", 
                                        "text": f"{user_input}\n\nYou also receive a screenshot of my screen as image data. Use the screenshot to answer as specifically as possible."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{encoded_string}"
                                        }
                                    }
                                ]
                            },
                        ],
                    )
                else:
                    # Standard fast text response
                    response = client.chat.completions.create(model=MODEL_NAME, messages=messages)

                ai_text = response.choices[0].message.content

                chat_history.append({"role": "assistant", "content": ai_text})
                if len(chat_history) > MAX_HISTORY:
                    chat_history = chat_history[-MAX_HISTORY:]

                execution_result = extract_and_run(ai_text)

                if execution_result:
                    # Feed result back BEFORE speaking, let AI comment naturally
                    chat_history.append(
                        {"role": "user", "content": f"SYSTEM OUTPUT: {execution_result}"}
                    )
                    messages_with_result = [system_prompt] + chat_history
                    final_res = client.chat.completions.create(
                        model=MODEL_NAME, messages=messages_with_result
                    )
                    final_text = final_res.choices[0].message.content
                    speak(final_text)
                    chat_history.append({"role": "assistant", "content": final_text})
                else:
                    # No code ran, just speak the response
                    speak(ai_text)
            except Exception as e:
                print(f"[!] ERROR: {e}")

    except KeyboardInterrupt:
        print("\n[!] FORCE QUIT.")
        speak("Shutting down.")
        sys.exit(0)

if __name__ == "__main__":
    main()