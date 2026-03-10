# DESCRIPTION: This script is designed to retrieve and read the current weather forecast for a specific location, allowing users to easily stay informed about the weather using voice commands.
# --- AUTONOMOUSLY GENERATED SKILL ---

import requests
import json

def get_weather_forecast(api_key, location):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": api_key,
        "units": "metric"
    }
    response = requests.get(base_url, params=params)
    weather_data = response.json()
    return weather_data

def main():
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # replace with your API key
    location = input("Enter the location (city, country code): ")
    weather_data = get_weather_forecast(api_key, location)
    print("Current weather forecast:")
    print(f"Weather: {weather_data['weather'][0]['description']}")
    print(f"Temperature: {weather_data['main']['temp']}°C")
    print(f"Humidity: {weather_data['main']['humidity']}%")
    print(f"Wind speed: {weather_data['wind']['speed']} m/s")

if __name__ == "__main__":
    main()