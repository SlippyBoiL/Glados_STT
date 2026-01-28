import google.generativeai as genai
import os

# --- PASTE YOUR KEY HERE ---
API_KEY = "AIzaSyAeFhU-9R1QUQHHBNidr7dLOAAmMFHanwc"

genai.configure(api_key=API_KEY)

print("--- CHECKING YOUR AVAILABLE MODELS ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"FOUND: {m.name}")
except Exception as e:
    print(f"ERROR: {e}")