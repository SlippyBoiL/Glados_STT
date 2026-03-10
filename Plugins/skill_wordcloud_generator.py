# DESCRIPTION: Word frequency from sample text (top words).
# --- GLADOS SKILL: skill_wordcloud_generator.py ---


def generate_wordcloud(input_text):
    words = input_text.lower().split()
    freq = {}
    for w in words:
        w = w.strip(".,!?;:")
        if w:
            freq[w] = freq.get(w, 0) + 1
    return freq


def main():
    sample = "The quick brown fox jumps over the lazy dog. The fox is quick and the dog is lazy."
    freq = generate_wordcloud(sample)
    top = sorted(freq.items(), key=lambda x: -x[1])[:10]
    print("Top words:")
    for word, count in top:
        print(f"  {word}: {count}")


if __name__ == "__main__":
    main()
