import os
import re
import subprocess
import sys
import time
import json
import threading
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
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")

# --- EXECUTION SAFETY ---
# NOTE: Actions run automatically from model-generated Python,
# but still go through a simple safety filter.
REQUIRE_EXECUTION_CONFIRMATION = False

# Allowlist: where actions are allowed to touch on disk.
# If you really want "entire computer", set this to ["C:\\"] (still confirmation-gated).
ALLOWED_PATH_ROOTS = [r"C:\\"]

# Simple denylist for obviously destructive operations (best-effort, not perfect).
DENYLIST_PATTERNS = [
    r"\bformat\s+[a-z]:\b",
    r"\bshutdown\s*/[sr]\b",
    r"\brmdir\b|\brm\s+-rf\b|\bdel\s+/f\b|\berase\b",
    r"System32",
    r"bcdedit",
    r"cipher\s+/w",
    r"reg\s+delete",
]

client = OpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

# --- AUDIO / TTS ---
VOICE_VOLUME = 1.0       # 0.1 (quiet) .. 1.0 (full)
PLAYBACK_SPEED = 1.15    # >1.0 = slightly faster, higher pitch

# --- CLEANER (Fixed: Uses Double Quotes to prevent Syntax Error) ---
def clean_text_for_speech(text):
    # Strip out fenced code blocks entirely so they aren't spoken.
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Strip inline code spans.
    text = re.sub(r"`[^`]+`", "", text)

    # Remove bibliography-style brackets like [1]
    text = re.sub(r"\[\d+\]", "", text)

    # Remove literal backslashes safely
    text = text.replace("\\", "")

    # Mask file-system style paths so they are not spoken verbatim
    # Windows paths like C:\Users\Name\foo.txt
    text = re.sub(r"\b[a-zA-Z]:\\[^\s'\"`]+", "that file path", text)
    # Unix-ish paths like /home/user/file or relative ./foo/bar
    text = re.sub(r"(?<![a-zA-Z0-9])(/[^ \t\n\r'\"`]+)", "that path", text)

    # Strip simple markdown formatting
    text = text.replace("**", "").replace("###", "")

    return text.strip()


def _load_settings():
    global VOICE_VOLUME
    if not os.path.exists(SETTINGS_PATH):
        return
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vol = float(data.get("voice_volume", VOICE_VOLUME))
        VOICE_VOLUME = max(0.1, min(1.5, vol))
    except Exception as e:
        print(f"[!] Failed to load settings: {e}")


def _save_settings():
    try:
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"voice_volume": VOICE_VOLUME}, f)
    except Exception as e:
        print(f"[!] Failed to save settings: {e}")


# --- THE MOUTH ---
def speak(text):
    clean_text = clean_text_for_speech(text)
    print(f"\nGLADOS: {clean_text}")
    print("[*] Generating audio...")

    def _do_tts(payload_text: str):
        try:
            response = requests.post(
                f"{ALLTALK_HOST}/api/tts-generate",
                data={
                    "text_input": payload_text,
                    "character_voice_gen": VOICE_NAME,
                    "language": "en",
                },
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
                        # Apply simple software volume control and playback speed
                        try:
                            scaled = data * VOICE_VOLUME
                            # clip to [-1, 1] if ndarray
                            if hasattr(scaled, "clip"):
                                scaled = scaled.clip(-1.0, 1.0)
                            sd.play(scaled, int(samplerate * PLAYBACK_SPEED))
                        except Exception:
                            # Fallback: play raw if scaling fails
                            sd.play(data, int(samplerate * PLAYBACK_SPEED))
                        sd.wait()
                except Exception:
                    pass
        except Exception as e:
            print(f"[!] AUDIO FAILED: {e}")

    # Run audio playback in a background thread so we can listen/interrupt.
    threading.Thread(target=_do_tts, args=(clean_text,), daemon=True).start()

# --- THE HANDS ---
def execute_python_code(code_block):
    filename = "runtime_action.py"
    filepath = os.path.join(PLUGINS_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code_block)
    
    print(f"[*] RUNNING CODE (confirmation-gated)...")
    try:
        result = subprocess.run([sys.executable, filepath], capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if not output: output = "Done."
        return output
    except Exception as e:
        return f"Error: {e}"

def _looks_dangerous(code: str) -> bool:
    lower = code.lower()
    for pat in DENYLIST_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return True
    return False

def _mentions_disallowed_paths(code: str) -> bool:
    # Best-effort: blocks obvious absolute paths outside allowlist.
    # (Not a full sandbox; the primary control is the confirmation gate.)
    roots = [os.path.abspath(r) for r in ALLOWED_PATH_ROOTS]
    if not roots:
        return True

    # Find Windows-y absolute paths like C:\something
    candidates = re.findall(r"\b[a-zA-Z]:\\[^\s'\"\n\r]+", code)
    for p in candidates:
        ap = os.path.abspath(p)
        if not any(ap.startswith(root) for root in roots):
            return True
    return False

def confirm_execution(code: str) -> bool:
    if not REQUIRE_EXECUTION_CONFIRMATION:
        return True

    print("\n--- ACTION REQUEST (needs approval) ---")
    print(code.strip())
    print("--- END ACTION ---")
    ans = input("Type YES to run (anything else cancels): ").strip()
    return ans == "YES"

def extract_and_run(ai_text):
    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        code = code_match.group(1)
        # Block obvious destructive actions even if approved.
        if _looks_dangerous(code) or _mentions_disallowed_paths(code):
            speak("Blocked.")
            return "Blocked unsafe action request."

        if not confirm_execution(code):
            speak("Cancelled.")
            return "Cancelled by user."

        speak("Running.")
        return execute_python_code(code)
    return None

# --- THE EARS ---
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\nListening...")
        # Calibrate to ambient noise, then make threshold slightly less sensitive.
        r.adjust_for_ambient_noise(source, duration=1.0)
        r.energy_threshold = max(r.energy_threshold * 1.5, 400)
        r.pause_threshold = 0.8
        try:
            # Longer timeout/phrase limit so you have more time to speak.
            audio = r.listen(source, timeout=12, phrase_time_limit=10)
            text = r.recognize_google(audio)
            print(f"YOU: {text}")
            return text
        except:
            return ""


# --- VOLUME CONTROL HELPERS ---
WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100,
}


def handle_volume_command(text: str) -> bool:
    """
    Detect volume commands like:
    - 'turn yourself down'
    - 'be quieter'
    - 'volume up / down'
    - 'set your volume to 30 percent'
    - 'volume 30'
    - 'volume seventy'

    Returns True if the command was handled and no LLM call is needed.
    """
    global VOICE_VOLUME

    lower = text.lower()
    if not any(k in lower for k in ("volume", "quieter", "louder", "too loud", "too quiet")):
        return False

    # Explicit percentage: "... 30 percent"
    m = re.search(r"(\d{1,3})\s*percent", lower)
    if m:
        pct = max(5, min(150, int(m.group(1))))
        VOICE_VOLUME = pct / 100.0
        speak(f"Volume {pct} percent.")
        _save_settings()
        return True

    # Bare number: "volume 30"
    m2 = re.search(r"\b(\d{1,3})\b", lower)
    if m2:
        pct = max(5, min(150, int(m2.group(1))))
        VOICE_VOLUME = pct / 100.0
        speak(f"Volume {pct} percent.")
        _save_settings()
        return True

    # Spelled-out number: "volume seventy"
    for word in lower.split():
        if word in WORD_NUMBERS:
            pct = max(5, min(150, WORD_NUMBERS[word]))
            VOICE_VOLUME = pct / 100.0
            speak(f"Volume {pct} percent.")
            _save_settings()
            return True

    # Down / quieter
    if any(k in lower for k in ("down", "quieter", "too loud", "lower")):
        VOICE_VOLUME = max(0.1, VOICE_VOLUME - 0.2)
        speak(f"Volume {int(VOICE_VOLUME * 100)} percent.")
        _save_settings()
        return True

    # Up / louder
    if any(k in lower for k in ("up", "louder", "too quiet", "raise", "increase")):
        VOICE_VOLUME = min(1.5, VOICE_VOLUME + 0.2)
        speak(f"Volume {int(VOICE_VOLUME * 100)} percent.")
        _save_settings()
        return True

    return False


# --- INTERRUPT HELPERS ---
def handle_interrupt_command(text: str) -> bool:
    """
    Let the user interrupt speech with phrases like:
    - 'stop talking'
    - 'be quiet'
    - 'shut up'
    - 'stop speaking'
    """
    lower = text.lower()
    if not any(k in lower for k in ("stop talking", "stop speaking", "be quiet", "shut up", "quiet")):
        return False

    try:
        sd.stop()
    except Exception as e:
        print(f"[!] Failed to stop audio: {e}")
    print("[*] Speech interrupted by user command.")
    return True


# --- APPLICATION HELPER UTILITIES ---
def _find_windows_executable(app_name: str) -> str | None:
    """
    Best-effort search for an EXE in common install locations,
    e.g. Program Files / Program Files (x86).
    """
    exe_name = app_name if app_name.lower().endswith(".exe") else f"{app_name}.exe"

    roots = [
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramW6432", r"C:\Program Files"),
    ]

    for root in roots:
        if not root or not os.path.isdir(root):
            continue

        # Directly inside the root
        direct = os.path.join(root, exe_name)
        if os.path.exists(direct):
            return direct

        # Inside a folder that roughly matches the app name
        try:
            for entry in os.listdir(root):
                full = os.path.join(root, entry)
                if os.path.isdir(full) and app_name.lower() in entry.lower():
                    cand = os.path.join(full, exe_name)
                    if os.path.exists(cand):
                        return cand
        except Exception:
            continue

    return None


# --- APPLICATION LAUNCH HELPERS ---
APP_LAUNCH_KEYWORDS = {
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
}

def handle_app_open_command(text: str) -> bool:
    """
    Open common applications on Windows when the user says e.g.:
    - 'open notepad'
    - 'start chrome'
    - 'open file explorer'

    Returns True if we launched something and no LLM call is needed.
    """
    lower = text.lower()
    if not any(k in lower for k in ("open", "start", "launch", "run")):
        return False

    print(f"[*] App-intent heard: {lower!r}")

    # First, check known common apps.
    for key, exe in APP_LAUNCH_KEYWORDS.items():
        if key in lower:
            try:
                if os.name == "nt":
                    # Try direct, then shell, then startfile.
                    try:
                        subprocess.Popen([exe])
                    except Exception:
                        try:
                            subprocess.Popen(exe, shell=True)
                        except Exception:
                            os.startfile(exe)
                else:
                    subprocess.Popen([exe])
                speak(f"Opening {key}.")
                return True
            except Exception as e:
                print(f"[!] Failed to open {key}: {e}")
                speak("Could not open it.")
                return True

    # Fallback: try to infer an arbitrary app name after 'open/start/launch/run'
    m = re.search(r"(open|start|launch|run)\s+(.+)", lower)
    if m:
        raw_name = m.group(2).strip(" .!?\t")
        # Remove generic words
        for junk in ("the", "app", "application", "program"):
            raw_name = raw_name.replace(" " + junk, "").replace(junk + " ", "")
        raw_name = raw_name.strip()

        if raw_name:
            print(f"[*] Generic app target parsed: {raw_name!r}")

            if os.name == "nt":
                # Try to locate a matching EXE in common install roots.
                found = _find_windows_executable(raw_name)
                if found:
                    try:
                        os.startfile(found)
                        speak(f"Opening {raw_name}.")
                        return True
                    except Exception as e:
                        print(f"[!] Failed to start '{found}': {e}")

            candidates = [raw_name, f"{raw_name}.exe"]
            for cand in candidates:
                try:
                    if os.name == "nt":
                        # Try direct, then shell, then startfile.
                        try:
                            subprocess.Popen([cand])
                        except Exception:
                            try:
                                subprocess.Popen(cand, shell=True)
                            except Exception:
                                os.startfile(cand)
                    else:
                        subprocess.Popen([cand])
                    speak(f"Opening {raw_name}.")
                    return True
                except Exception as e:
                    print(f"[!] Failed to open '{cand}': {e}")
            speak("Could not open it.")
            return True

    return False


# --- APPLICATION CLOSE HELPERS ---
PROC_NAME_KEYWORDS = {
    "notepad": "notepad.exe",
    "calculator": "calculator.exe",
    "calc": "calculator.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "steam": "steam.exe",
}

def handle_app_close_command(text: str) -> bool:
    """
    Close applications by killing their process, e.g.:
    - 'close chrome'
    - 'quit steam'
    - 'exit notepad'
    """
    lower = text.lower()
    if not any(k in lower for k in ("close", "quit", "exit", "shut down", "shutdown", "kill")):
        return False

    proc_name = None
    for key, pname in PROC_NAME_KEYWORDS.items():
        if key in lower:
            proc_name = pname
            break

    if not proc_name:
        m = re.search(r"(close|quit|exit|kill)\s+(.+)", lower)
        if m:
            raw = m.group(2).strip(" .!?\t")
            for junk in ("the", "app", "application", "program"):
                raw = raw.replace(" " + junk, "").replace(junk + " ", "")
            raw = raw.strip()
            if raw:
                proc_name = raw if raw.lower().endswith(".exe") else f"{raw}.exe"

    if not proc_name:
        return False

    print(f"[*] Close-intent for process: {proc_name!r}")

    if os.name == "nt":
        try:
            # /T ensures child processes are also closed when possible.
            result = subprocess.run(
                ["taskkill", "/IM", proc_name, "/F", "/T"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                speak("Closed.")
            else:
                print(f"[!] taskkill output for {proc_name}: {result.stdout} {result.stderr}")
                speak("Could not close it.")
            return True
        except Exception as e:
            print(f"[!] Failed to close {proc_name}: {e}")
            speak("Could not close it.")
            return True

    # Non-Windows: best-effort with pkill
    try:
        subprocess.run(
            ["pkill", "-f", proc_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        speak("Closed.")
        return True
    except Exception as e:
        print(f"[!] Failed to close {proc_name}: {e}")
        speak("Could not close it.")
        return True

# --- MAIN LOOP ---
def main():
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)

    # Restore persisted settings like last volume.
    _load_settings()

    # --- SYSTEM RULES ---
    messages = [{
        "role": "system",
        "content": (
            "You are GLADOS, a local Windows control assistant.\n"
            "You control this PC by generating Python the user may execute.\n"
            "Assume your Python can touch any file, program, or setting allowed by Windows.\n"
            "Rules:\n"
            "- Answers must be very short (about 5–8 words) unless you are outputting code.\n"
            "- For control requests, respond with ONLY a ```python``` block that performs the action, no extra explanation.\n"
            "- For normal conversation, avoid code and jargon; reply in plain, simple sentences.\n"
            "- Treat code you emit as if it will be executed on this machine.\n"
            "- You may read your own files (like Kernel.py) and write helper/debug code into separate files under the plugins folder when needed.\n"
            "- Do not talk about limitations; focus on direct, working control code."
        )
    }]

    print(f"--- CORE ONLINE ({MODEL_NAME}) ---")
    
    # Check connection to AllTalk
    try:
        requests.get(f"{ALLTALK_HOST}/api/ready", timeout=2)
        speak("Online.")
    except:
        print("\n[!] WARNING: AllTalk Voice Server is NOT running.")
        print("[!] Please double-click 'start_alltalk.bat' first!\n")

    while True:
        user_input = listen()
        if not user_input: continue

        if "exit" in user_input.lower():
            break

        # Allow user to interrupt current speech output.
        if handle_interrupt_command(user_input):
            continue

        # Close apps by voice
        if handle_app_close_command(user_input):
            continue

        # Simple built-in commands that don't need the LLM
        if handle_app_open_command(user_input):
            continue

        # Let the assistant "turn itself down" on request,
        # without needing an LLM round-trip.
        if handle_volume_command(user_input):
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            print("[*] Thinking...")
            response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
            ai_text = response.choices[0].message.content
            
            execution_result = extract_and_run(ai_text)
            
            if execution_result:
                clean_ai_text = clean_text_for_speech(ai_text)
                messages.append({"role": "assistant", "content": clean_ai_text})
                messages.append({"role": "user", "content": f"SYSTEM OUTPUT:\n{execution_result}"})
                
                final_res = client.chat.completions.create(model=MODEL_NAME, messages=messages)
                final_text = final_res.choices[0].message.content
                speak(final_text)
                messages.append({"role": "assistant", "content": final_text})
            else:
                speak(ai_text)
                messages.append({"role": "assistant", "content": ai_text})

        except Exception as e:
            print(f"[!] ERROR: {e}")

if __name__ == "__main__":
    main()