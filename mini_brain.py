import numpy as np

class GLaDOS_Synapse:
    def __init__(self):
        # Seed the random number generator so it learns the same way each time
        np.random.seed(1)
        # Create a 3x1 matrix of random weights (from -1 to 1) for our 3 inputs
        self.weights = 2 * np.random.random((3, 1)) - 1

    def sigmoid(self, x):
        # The activation function that turns numbers into probabilities
        return 1 / (1 + np.exp(-x))

    def sigmoid_derivative(self, x):
        # The gradient used to correct mistakes during training
        return x * (1 - x)

    def train(self, inputs, outputs, iterations):
        # The core learning loop: Guess, Check Error, Adjust
        for _ in range(iterations):
            guess = self.think(inputs)
            error = outputs - guess
            adjustments = np.dot(inputs.T, error * self.sigmoid_derivative(guess))
            self.weights += adjustments

    def think(self, inputs):
        # Matrix multiplication of inputs and weights, passed through the sigmoid
        return self.sigmoid(np.dot(inputs, self.weights))