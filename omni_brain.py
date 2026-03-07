import tensorflow as tf
import numpy as np


# 1. THE TRAINING DATA (Teaching the brain what commands look like)
# We give it examples, and label them:
# 0 = Light Command, 1 = Open App, 2 = Close App, 3 = Chat/Skill
training_sentences = [
    # 0 = LIGHT CONTROL (14 items)
    "turn on the bedroom lights", "make the tv red", "lights off", "dim the closet to 50%", "turn the strip blue",
    "illuminate the room", "shut off the lights", "brightness to 100", "set lights to warm", "pitch black",
    "give me some light", "it is too dark in here", "govee lights on", "change the bedroom to purple",

    # 1 = OPEN APP (10 items)
    "open google chrome", "start discord", "launch steam", "boot up vs code", "open calculator",
    "fire up the browser", "start my game client", "open up spotify", "launch edge", "run notepad",

    # 2 = CLOSE APP (10 items)
    "kill steam", "close notepad", "terminate discord", "shut down chrome", "quit edge",
    "destroy spotify", "force quit calculator", "stop the browser", "exit vs code", "close everything",

    # 3 = CHAT / SKILLS
    "hello glados", "write a python script for me", "what is the meaning of life", "you are terrible",
    "save this skill", "how do i bake a cake", "what is the weather", "tell me a joke", "you are a useless machine",
    "run the diagnostic", "Open skill file", "show me file path", "what is file path?", "Manage skills",
    "list skills", "add skill", "import skills", "import skills from file", "import skills from text",
    "Calculate average of 10 largest primes from 1 to 1000", "Find average of 10 largest prime numbers",
    "parse code file", "create new skills", "extract programming knowledge", "Clean up temp files",
    "tidy temp", "delete temp files", "Flip a coin", "Calculate two event combine probability",
    "Get OS details", "tell me about my OS", "what am I running?", "start datestamp generator",
    "Define a word", "define a phrase", "define a term", "Tell me a fact", "show me something new",
    "share an interesting fact", "Rename file with timestamp", "prevent conflicts", "update filename",
    "generate filename", "create folder", "rename file", "Generate a random casual date",
    "Generate skill certificate", "create skill certificate template", "create certificate for skill",
    "Generate encrypted file path", "Generate a password", "create a strong password", "create a random password",
    "Give me a random quote", "Quote me something", "Read a quote", "What is the AI tool for", "tell me",
    "can it write code", "generate token", "retrieve token", "track token usage", "Generate SHA256 checksum",
    "hash password", "generate hash", "encrypt password", "Where is the International Space Station now",
    "show me", "what is the ISS location", "Find largest prime factor", "log skill", "log skill with message",
    "log skill with timestamp", "Find domain information", "look up domain", "what is domain status",
    "find prime numbers up to a given number", "Check internet latency", "Check latency", "What's my internet speed",
    "Commit and push to GitHub", "update project", "sync with GitHub", "What files are most used",
    "what files are used most", "generate a random alphabet", "generate sequential file", "verify compressed size",
    "create large file", "Generate username", "create random username", "make username", "generate ransom note",
    "Schedule shutdown", "abort shutdown", "cancel shutdown", "pause for 1 minute", "wait a bit", "take a break",
    "What device information", "show me specs", "tell me about my computer", "Show me system info", "get user details",
    "display password hash", "Create task manager", "list tasks", "assign task", "Remind me of upcoming tasks",
    "remind me of deadlines", "remind me of appointments", "Create directory structure", "create timestamp directory",
    "create organized directory", "compare files in directory", "verify uniqueness based on hash", "find duplicate files",
    "Show me the last modified file", "Run virus simulation", "print installation message", "generate malware code",
    "what's the weather like today", "Is the website up", "check its status", "can you ping the website",
    "What is my WiFi password", "Get my public IP", "get my location"
]

# --- DYNAMIC LABELS ---
# Automatically math out the array so you never have to count it again!
training_labels = np.array(
    [0] * 14 +  # First 14 are Lights
    [1] * 10 +  # Next 10 are Open App
    [2] * 10 +  # Next 10 are Close App
    [3] * (len(training_sentences) - 34)  # Everything else belongs to Chat/Skills
)


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