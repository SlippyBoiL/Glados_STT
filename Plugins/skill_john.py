# DESCRIPTION: Script for analyzing skill-related data.
# --- GLADOS SKILL: skill_john.py ---

import datetime
import json
import uuid

class Skill: pass

class SkillWordCount:
    @staticmethod
    def count_words_in_text(text):
        words = text.split()
        return {word: words.count(word) for word in set(words)}

    @staticmethod
    def save_word_frequency_to_json(filename, frequency_dict):
        with open(filename, 'w') as file:
            json.dump(frequency_dict, file, indent=4)

    @staticmethod
    def load_word_frequency_from_json(filename):
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

class SkillWordRanker:
    @staticmethod
    def rank_words_by_frequencies(frequency_dict):
        return sorted(frequency_dict.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def generate_top_ranked_word_list(filename, num_words):
        frequency_dict = SkillWordCount.load_word_frequency_from_json(filename)
        return SkillWordRanker.rank_words_by_frequencies(frequency_dict)[:num_words]

class SkillRandomUsernameGenerator:
    @staticmethod
    def generate_username(length):
        characters = 'abcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join([char for char in characters for _ in range(length)])

def main():
    filename = 'word_frequency.json'
    length = 10
    num_words = 10

    text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "

    frequency_dict = SkillWordCount.count_words_in_text(text)
    SkillWordCount.save_word_frequency_to_json(filename, frequency_dict)

    top_ranked_word_list = SkillWordRanker.generate_top_ranked_word_list(filename, num_words)

    print("Top {} ranked words:".format(num_words))
    for word, frequency in top_ranked_word_list:
        print("{}: {}".format(word, frequency))

    generator = SkillRandomUsernameGenerator
    generated_username = generator.generate_username(length)
    print("\nGenerated Random Username: {}".format(generated_username))

if __name__ == "__main__":
    main()