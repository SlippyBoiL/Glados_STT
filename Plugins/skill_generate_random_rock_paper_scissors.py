# DESCRIPTION: One round of random rock-paper-scissors (player vs computer).
# --- GLADOS SKILL: skill_generate_random_rock_paper_scissors.py ---

import random


def play_one_round():
    options = ["rock", "paper", "scissors"]
    player = random.choice(options)
    computer = random.choice(options)
    print(f"Player: {player}  |  Computer: {computer}")
    if player == computer:
        print("Tie.")
    elif (player == "rock" and computer == "scissors") or (
        player == "scissors" and computer == "paper"
    ) or (player == "paper" and computer == "rock"):
        print("Player wins.")
    else:
        print("Computer wins.")


def main():
    play_one_round()


if __name__ == "__main__":
    main()
