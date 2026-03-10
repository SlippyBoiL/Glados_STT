# DESCRIPTION: Counts the occurrences of each word in a given text.
# --- GLADOS SKILL: skill_word_count.py ---


def count_words(text):
    words = text.split()
    word_count = {}
    for word in words:
        w = word.lower().strip(".,!?;:")
        if w:
            word_count[w] = word_count.get(w, 0) + 1
    return word_count


def main():
    sample = "The quick brown fox jumps over the lazy dog. The fox is quick."
    word_count = count_words(sample)
    print("Word count (sample):")
    for word, count in sorted(word_count.items(), key=lambda x: -x[1]):
        print(f"  {word}: {count}")


if __name__ == "__main__":
    main()
