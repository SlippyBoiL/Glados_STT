# DESCRIPTION: Retrieves the password for the current WiFi connection.
# --- GLADOS SKILL: skill_wifi_pass.py ---

import subprocess
import re

def get_wifi_pass():
    try:
        # Get current SSID
        meta_data = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'])
        decoded = meta_data.decode('utf-8', errors="backslashreplace")
        ssid_match = re.search(r"^\s+SSID\s+:\s+(.*)$", decoded, re.MULTILINE)
        
        if not ssid_match:
            return "No WiFi connection active."
            
        ssid = ssid_match.group(1).strip()
        
        # Get Profile
        profile_data = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', ssid, 'key=clear'])
        decoded_profile = profile_data.decode('utf-8', errors="backslashreplace")
        pass_match = re.search(r"Key Content\s+:\s+(.*)$", decoded_profile, re.MULTILINE)
        
        password = pass_match.group(1).strip() if pass_match else "OPEN NETWORK"
        return f"Network: {ssid} | Password: {password}"
    except Exception as e:
        return f"Extraction failed: {e}"

if __name__ == "__main__":
    print(get_wifi_pass())