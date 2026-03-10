# DESCRIPTION: A Python script listing the names of planets in our solar system, including their order of appearance in our solar system.")
# --- GLADOS SKILL: skill_solar_system.py ---

# skill_solar_system.py

import datetime

def get_current_year():
    """Gets the current year."""
    return datetime.datetime.now().year

def get_planets_name():
    """Returns the name of planets in the solar system."""
    return [
        'Mercury',  # 1st planet
        'Venus',  # 2nd planet
        'Mars',  # 3rd planet
        'Jupiter',  # 4th planet
        'Saturn',  # 5th planet
        'Uranus',  # 6th planet
        'Neptune',  # 7th planet
    ]

def main():
    year = get_current_year()
    print(f"The current year is: {year}")

    planets_name = get_planets_name()
    print("The planets in our solar system are:")
    for i, planet in enumerate(planets_name, 1):
        print(f"{i}. {planet}")
    print()

if __name__ == "__main__":
    main()