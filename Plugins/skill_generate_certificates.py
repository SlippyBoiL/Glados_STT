# DESCRIPTION: Generates a simple certificate text file with timestamp.
# --- GLADOS SKILL: skill_generate_certificates.py ---

import datetime
import random


def skill_generate_certificates(skill_name="GLaDOS Skill"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cert_id = random.randint(10000, 99999)
    return f"Certificate #{cert_id} — {skill_name} — Generated: {timestamp}"


def main():
    cert = skill_generate_certificates()
    print(cert)
    filename = f"certificate_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
    with open(filename, "w") as f:
        f.write(cert)
    print(f"Saved to {filename}")


if __name__ == "__main__":
    main()
