# DESCRIPTION: Calculates two-event combined probability and lists directory contents.
# --- GLADOS SKILL: skill_combinatorics.py ---

import os


def two_event_probability(p1, p2):
    """Probability of both independent events: P(A and B) = P(A) * P(B)."""
    return float(p1) * float(p2)


def main():
    # Example: two coin flips (0.5 * 0.5 = 0.25)
    p = two_event_probability(0.5, 0.5)
    print(f"Two-event combine (e.g. two heads): {p:.1%}")
    print("Files in current directory:")
    for f in sorted(os.listdir("."))[:20]:
        print(f"  {f}")
    if len(os.listdir(".")) > 20:
        print("  ...")


if __name__ == "__main__":
    main()
