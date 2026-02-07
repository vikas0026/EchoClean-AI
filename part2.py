# part2.py
from detoxify import Detoxify

print(" Loading Detoxify model (first time may take a few seconds)...")
model = Detoxify("original")
print(" Detoxify model loaded successfully.")

TOXIC_THRESHOLD = 0.75

def filter_toxicity(text):
    """
    Detect and censor toxic words in text.
    Returns cleaned text with **** replacements.
    """
    if not text.strip():
        return text

    words = text.split()
    filtered_words, flagged = [], []

    for word in words:
        tox_score = float(model.predict(word)["toxicity"])
        if tox_score > TOXIC_THRESHOLD:
            filtered_words.append("****")
            flagged.append((word, round(tox_score, 3)))
        else:
            filtered_words.append(word)

    if flagged:
        print(f"🚫 Toxic words: {flagged}")
    else:
        print("✅ Clean text.")

    return " ".join(filtered_words)
