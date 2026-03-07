# DESCRIPTION: ```python
# --- GLADOS SKILL: skill_generate_random_rock_paper_scissors.py ---

# skill_generate_random_rock_paper_scissors.py

import random

def generate_game():
    options = ["rock", "paper", "scissors"]
    player_choice = random.choice(options)
    computer_choice = random.choice(options)

    print(f"Player chose: {player_choice}")
    print(f"Computer chose: {computer_choice}")

    if player_choice == computer_choice:
        print("It's a tie!")
    elif (player_choice == "rock" and computer_choice == "scissors") or \
         (player_choice == "scissors" and computer_choice == "paper") or \
         (player_choice == "paper" and computer_choice == "rock"):
        print("Player wins!")
    else:
        print("Computer wins!")

def main():
    while True:
        generate_game()
        play_again = input("Do you want to play again? (yes/no): ")
        if play_again.lower() != "yes":
            break

if __name__ == "__main__":
    main()