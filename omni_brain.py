import tensorflow as tf
import numpy as np
import json
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle

# --- NEUROPLASTICITY: DYNAMIC MEMORY BANK ---
# We load the vocabulary directly from the JSON file
memory_file = "brain_data.json"

if not os.path.exists(memory_file):
    print(f"[!] Critical Error: {memory_file} is missing. GLaDOS has amnesia.")
    exit()

with open(memory_file, "r", encoding="utf-8") as f:
    brain_data = json.load(f)

training_sentences = []
labels_list = []

# Map the string categories from JSON directly to the integer Intents
intent_map = {
    "LIGHTS": 0,
    "OPEN_APP": 1,
    "CLOSE_APP": 2,
    "CHAT_SKILLS": 3
}

# Dynamically construct the arrays!
for category, sentences in brain_data.items():
    if category in intent_map:
        intent_id = intent_map[category]
        training_sentences.extend(sentences)
        # Automatically generate the correct number of labels for this category
        labels_list.extend([intent_id] * len(sentences))

training_labels = np.array(labels_list)

# ... The rest of your omni_brain.py code (Tokenizer, model building, etc.) continues here ...



_model = None


def build_and_train_model():
    """Builds (if needed) and trains the intent classifier brain."""
    global _model
    if _model is not None:
        return _model

    print("Waking up TensorFlow... (Ignore any GPU warnings)")

    # 2. TEXT VECTORIZATION (Converting words into math)
    # Slightly larger vocab and sequence length for better generalization.
    vectorizer = tf.keras.layers.TextVectorization(
        max_tokens=2000,
        output_sequence_length=20,
    )
    # Adapt on a Tensor of strings (avoids NumPy conversion issues)
    vectorizer.adapt(tf.constant(training_sentences, dtype=tf.string))

    # 3. BUILD THE BRAIN ARCHITECTURE
    # Slightly larger embedding and dense layer with dropout to improve robustness.
    model = tf.keras.models.Sequential([
        vectorizer,
        tf.keras.layers.Embedding(input_dim=2000, output_dim=32, name="Word_Understanding"),
        tf.keras.layers.GlobalAveragePooling1D(name="Context_Averaging"),
        tf.keras.layers.Dense(32, activation="relu", name="Logic_Processing"),
        tf.keras.layers.Dropout(0.2, name="Overfit_Safety"),
        tf.keras.layers.Dense(4, activation="softmax", name="Final_Decision"),
    ])

    # 4. COMPILE AND TRAIN
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    print("\nCommencing Neural Training Protocol...")
    # Train the brain with more epochs and a small batch size,
    # using early stopping on training loss to avoid overfitting too hard.
    x_train = tf.constant(training_sentences, dtype=tf.string)
    y_train = tf.convert_to_tensor(training_labels, dtype=tf.int32)
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="loss", patience=15, restore_best_weights=True
    )
    model.fit(
        x_train,
        y_train,
        epochs=300,
        batch_size=8,
        shuffle=True,
        verbose=0,
        callbacks=[early_stop],
    )
    print("[+] Brain fully formed and trained!\n")

    _model = model
    return _model


def get_model():
    """Returns a trained model instance, building it on first use."""
    return build_and_train_model()


# 5. TEST THE BRAIN ON NEW SENTENCES
def test_brain(sentence):
    model = get_model()
    prediction = model.predict(tf.constant([sentence], dtype=tf.string), verbose=0)[0]
    best_guess = np.argmax(prediction)
    confidence = prediction[best_guess] * 100
    
    categories = ["💡 LIGHT CONTROL", "🟢 OPEN APP", "🔴 CLOSE APP", "💬 CHAT / SKILL"]
    
    print(f"You said: '{sentence}'")
    print(f"GLaDOS Brain thinks it is: {categories[best_guess]} ({confidence:.2f}% confident)\n")


if __name__ == "__main__":
    # Let's test it with things it has NEVER seen before!
    print("--- TESTING THE NETWORK WITH NEW DATA ---")
    test_brain("illuminate my sleeping quarters")  # Never seen these words
    test_brain("fire up the web browser")          # Never seen "fire up" or "browser"
    test_brain("destroy spotify")                  # Never seen "destroy" or "spotify"
    test_brain("how do I bake a cake?")            # Never seen these words