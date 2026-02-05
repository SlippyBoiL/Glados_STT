# DESCRIPTION: Tracks the ISS location.
# --- GLADOS SKILL: skill_iss.py ---

import requests

def track_iss():
    try:
        data = requests.get("http://api.open-notify.org/iss-now.json").json()
        pos = data['iss_position']
        return f"ISS Location: Latitude {pos['latitude']}, Longitude {pos['longitude']}."
    except:
        return "Lost contact with orbital station."

if __name__ == "__main__":
    print(track_iss())