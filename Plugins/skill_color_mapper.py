# DESCRIPTION: A utility to generate and map color names to unique identifiers.`
# --- GLADOS SKILL: skill_color_mapper.py ---

# skill_unique_color_mapper.py

import random
import string

def generate_color():
    """Generate a random color in hexadecimal format."""
    return '#{:06x}'.format(random.randint(0, 0xFFFFFF))

def generate_color_name():
    """Generate a random color name from a predefined list."""
    color_names = ['Beige', 'Blue', 'Black', 'Brown', 'Grey', 'Green', 'Orange', 'Pink', 'Purple', 'Red', 'White', 'Yellow']
    return random.choice(color_names)

def map_color_to_name(color):
    """Map a color to its name."""
    color_map = {
        'Red': 'Red',
        'Blue': 'Blue',
        'Black': 'Black',
        'Green': 'Green'
    }
    return color_map.get(color, 'Unknown Color')

def generate_color_code():
    """Generate a unique color code."""
    return f'#{generate_color()}'

def main():
    """Example usage of the color mapper script."""
    color = generate_color()
    color_name = generate_color_name()
    color_code = generate_color_code()
    print(f"Color: {color} (Name: {map_color_to_name(color_name)})")
    print(f"Color Code: {generate_color_code()}")
    print(f"Color Name: {map_color_to_name(color)}")

if __name__ == "__main__":
    main()