import tensorflow as tf
import datetime

# 1. Define the "Brain" Architecture
# We are building a simple feed-forward neural network
model = tf.keras.models.Sequential([
  tf.keras.layers.Flatten(input_shape=(28, 28), name="Retina_Input"),
  tf.keras.layers.Dense(128, activation='relu', name="Frontal_Lobe"),
  tf.keras.layers.Dropout(0.2, name="Synapse_Pruning"),
  tf.keras.layers.Dense(10, activation='softmax', name="Output_Decision")
])

# 2. Compile the brain (giving it a learning objective)
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

# 3. Setup TensorBoard to record the brain forming
log_dir = "logs/fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

print("Brain architecture compiled. Creating dummy data to spark the network...")

# (Creating some random fake data just to make the brain "think" for a second)
import numpy as np
x_train = np.random.random((1000, 28, 28))
y_train = np.random.randint(10, size=(1000,))

# 4. Train the brain and log the data
model.fit(x_train, y_train, epochs=5, callbacks=[tensorboard_callback])

print("\n[+] Brain formation logged successfully!")