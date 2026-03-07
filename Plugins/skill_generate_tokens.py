# DESCRIPTION: This script generates and retrieves tokens using a dictionary to track their usage.
# --- GLADOS SKILL: skill_generate_tokens.py ---

import os
import uuid
import time

class TokenGenerator:
    def __init__(self):
        self.tokens = {}

    def generate_token(self):
        token = str(uuid.uuid4())
        self.tokens[token] = True
        return token

    def retrieve_token(self, token):
        if token in self.tokens:
            self.tokens[token] = False
            return True
        else:
            return False

def main():
    generator = TokenGenerator()

    # Generate a fixed token
    token = generator.generate_token()
    print(f"Fixed Token: {token}")

    # Check if token is valid
    print(f"Token Valid: {generator.retrieve_token(token)}")
    
    # Wait for a short duration
    time.sleep(0.5)

    # Generate a new token
    new_token = generator.generate_token()
    print(f"New Token: {new_token}")

    # Check if token is valid
    print(f"Token Valid: {generator.retrieve_token(new_token)}")

if __name__ == "__main__":
    main()