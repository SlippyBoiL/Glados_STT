# DESCRIPTION: This script generates a customized shopping list based on the user's voice assistant requests, automatically organizing items by category and adding missing items from a predefined pantry database.
# --- AUTONOMOUSLY GENERATED SKILL ---

import speech_recognition as sr
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from collections import defaultdict
import re

# Initialize NLTK data
nltk.download('wordnet')
nltk.download('stopwords')

# Define the pantry database
pantry_database = {
    'fruits': ['apple', 'banana', 'orange', 'grape'],
    'vegetables': ['carrot', 'broccoli', 'potato', 'tomato'],
    'dairy': ['milk', 'cheese', 'eggs', 'yogurt'],
    'meat': ['chicken', 'beef', 'pork', 'lamb'],
    'pasta': ['spaghetti', 'fettuccine', 'penne', 'lasagna'],
    'snacks': ['chips', 'popcorn', 'cookies', 'candy']
}

# Define the lemmatizer
lemmatizer = WordNetLemmatizer()

# Define the stop words
stop_words = set(stopwords.words('english'))

# Define the function to process the user's request
def process_request(request):
    # Initialize the result dictionary
    result = defaultdict(list)

    # Tokenize the request
    tokens = re.findall(r'\b\w+\b', request.lower())

    # Remove stop words and lemmatize the tokens
    tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]

    # Categorize the tokens
    for category in pantry_database:
        for token in tokens:
            if token in pantry_database[category]:
                result[category].append(token)

    return result

# Define the function to generate the shopping list
def generate_shopping_list(request):
    # Process the request
    result = process_request(request)

    # Initialize the shopping list
    shopping_list = []

    # Add items to the shopping list
    for category, items in result.items():
        for item in items:
            if item not in shopping_list:
                shopping_list.append(item)

    return shopping_list

# Define the function to add missing items to the shopping list
def add_missing_items(shopping_list, request):
    # Process the request
    result = process_request(request)

    # Add missing items to the shopping list
    for category, items in result.items():
        for item in items:
            if item not in shopping_list:
                shopping_list.append(item)

    return shopping_list

# Define the function to run the script
def run_script():
    # Initialize the speech recognition object
    r = sr.Recognizer()

    # Ask the user for their request
    with sr.Microphone() as source:
        print("Please say your request:")
        audio = r.listen(source)

    # Try to recognize the user's request
    try:
        request = r.recognize_google(audio)
        print("You said:", request)

        # Generate the shopping list
        shopping_list = generate_shopping_list(request)

        # Add missing items to the shopping list
        shopping_list = add_missing_items(shopping_list, request)

        # Print the shopping list
        print("Your shopping list is:")
        for item in shopping_list:
            print(item)

    except sr.UnknownValueError:
        print("Sorry, I didn't understand your request.")
    except sr.RequestError:
        print("Sorry, I couldn't connect to the speech recognition service.")

# Run the script
run_script()