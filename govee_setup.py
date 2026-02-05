import requests
import json

# PASTE YOUR API KEY HERE (you'll get this from Govee)
GOVEE_API_KEY = "a2e66167-cbe7-4416-93f7-d54c7f92c7b6"

def get_devices():
    """Fetches all your Govee devices."""
    url = "https://openapi.api.govee.com/router/api/v1/user/devices"
    headers = {
        "Govee-API-Key": GOVEE_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS! Found your devices:\n")
        print(json.dumps(data, indent=2))
        
        # Extract device info
        if "data" in data:
            devices = data["data"]
            print("\n" + "="*60)
            print("COPY THIS INFO TO YOUR CONFIG:")
            print("="*60)
            for device in devices:
                print(f"\nDevice: {device.get('deviceName', 'Unnamed')}")
                print(f"  Device ID: {device.get('device')}")
                print(f"  Model: {device.get('sku')}")
                print(f"  Controllable: {device.get('capabilities', [])}")
        
        return data
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 401:
            print("\n⚠️  Your API key is invalid. Check it and try again.")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("GOVEE DEVICE SCANNER")
    print("=" * 60)
    
    if GOVEE_API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️  You need to add your API key first!")
        print("1. Open Govee Home app")
        print("2. Settings → About Us → Apply for API Key")
        print("3. Paste your key at the top of this file")
        print("4. Run this script again")
    else:
        get_devices()
