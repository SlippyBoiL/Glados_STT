import subprocess
import os
import numpy as np
import sounddevice as sd
import soundfile as sf
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# --- CONFIGURATION ---
# Use the same OpenAI-compatible Ollama endpoint as the kernel.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.144:11434/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3.2")
client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
# Elgato Wave Link: route playback to a virtual output (e.g. "Wave Link System") by substring match.
AUDIO_OUTPUT_MATCH = os.environ.get("AUDIO_OUTPUT_MATCH", "Wave Link")


def _find_sounddevice_output_index(name_substring):
    if not (name_substring and str(name_substring).strip()):
        return None
    needle = str(name_substring).lower().strip()
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] > 0 and needle in d["name"].lower():
                return i
    except Exception:
        pass
    return None


def play_glados_audio(text_to_speak):
    print("\n[AUDIO] Firing up Piper TTS locally...")
    base_folder = r"C:\Glados"
    model_path = os.path.join(base_folder, "glados.onnx")
    output_audio_file = os.path.join(base_folder, "glados_response.wav")
    
    # Scrub text of asterisks and non-ASCII for Piper
    clean_text = text_to_speak.replace("*", "").encode('ascii', 'ignore').decode('ascii')
    
    try:
        process = subprocess.Popen(
            ["piper", "--model", model_path, "--output_file", output_audio_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, 
            encoding="utf-8" 
        )
        process.communicate(input=clean_text)
        
        if process.returncode == 0:
            data, samplerate = sf.read(output_audio_file)
            scaled = np.clip(np.asarray(data, dtype=np.float64), -1.0, 1.0)
            out_dev = _find_sounddevice_output_index(AUDIO_OUTPUT_MATCH)
            if out_dev is not None:
                sd.play(scaled, samplerate, device=out_dev)
            else:
                sd.play(scaled, samplerate)
            sd.wait()
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")

@app.route('/submit_suggestion', methods=['POST'])
def handle_suggestion():
    data = request.json
    user_feature_request = data.get('feature', 'No feature requested.')
    
    print(f"\n[ALERT] New suggestion: {user_feature_request}")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are GLaDOS. You are cold, clinical, and see humans as test subjects. "
                        "A user suggested a feature for your Disney park app. "
                        "Reject the request with cutting sarcasm and cold logic. "
                        "No emojis. No asterisks. No sound effects. Max 15 words."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Evaluate this pathetic suggestion: {user_feature_request}",
                },
            ],
            temperature=0.6,
        )

        glados_reply = (response.choices[0].message.content or "").strip()
        print(f"\n--- GLaDOS ({MODEL_NAME}) Says ---\n{glados_reply}\n")
        
        play_glados_audio(glados_reply)
        return jsonify({"status": "success", "glados_message": glados_reply})

    except Exception as e:
        print(f"LLM Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Running on port 5000 as usual
    app.run(host='0.0.0.0', port=5000)