# DESCRIPTION: This script generates a list of unique hexadecimal colors and then identifies the missing digits '0' from '9' in those colors.
# --- GLADOS SKILL: skill_color_generation.py ---

#!/usr/bin/env python3

import math
import os
import random
import sys

def generate_unique_colors():
    colors = []
    while len(colors) < 10:
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        colors.append(f"#{r:02x}{g:02x}{b:02x}")
    return colors

def find_missing_colors(colors):
    all_colors = set("0123456789abcdef")
    return set(colors) - all_colors

def generate_circular_shape(colors):
    shape = []
    while len(shape) < 10:
        color = random.choice(colors)
        x = random.randint(0, 100)
        y = random.randint(0, 100)
        shape.append((x, y, color))
    return shape

def main():
    colors = generate_unique_colors()
    print("Missing colors:", find_missing_colors(colors))
    print("Random color shape:")
    print(generate_circular_shape(colors))
    print("Colors used in circular shape:", [color for _, _, color in generate_circular_shape(colors)])

if __name__ == "__main__":
    main()

# Check for colors in file
if __name__ == "__main__":
    if os.path.exists("/usr/share/color-manual"):
        import colorsys
        with open("/usr/share/color-manual", "r") as file:
            print("Colors in /usr/share/color-manual:")
            colors = file.read().split("\n")
            print(colors)