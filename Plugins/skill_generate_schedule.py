# DESCRIPTION: This script, "Time Saver", generates a daily schedule with suggested tasks, breaks, and leisure activities to help users make the most of their time and increase productivity.
# --- AUTONOMOUSLY GENERATED SKILL ---

import random
import datetime

def generate_schedule():
    # Define tasks, breaks, and leisure activities
    tasks = [
        "Exercise",
        "Meditate",
        "Learn a new skill",
        "Read a book",
        "Write in a journal",
        "Practice a musical instrument",
        "Spend time with family/friends",
        "Get a massage",
        "Try a new recipe",
        "Watch a movie/TV show"
    ]

    breaks = [
        "Take a 10-minute break to stretch",
        "Drink a glass of water",
        "Eat a healthy snack",
        "Take a power nap",
        "Do a quick workout"
    ]

    leisure_activities = [
        "Play a sport",
        "Go for a walk",
        "Do a puzzle",
        "Play with a pet",
        "Take a relaxing bath",
        "Listen to music",
        "Take a nap",
        "Do some yoga",
        "Play a game"
    ]

    # Define the daily schedule
    schedule = {
        "Morning": {
            "6:00 AM - 7:00 AM": "Wake up and meditate",
            "7:00 AM - 8:00 AM": "Exercise",
            "8:00 AM - 9:00 AM": "Shower and get ready for the day",
            "9:00 AM - 10:00 AM": "Have breakfast and plan out your day"
        },
        "Mid-Morning": {
            "10:00 AM - 11:00 AM": "Work on a task",
            "11:00 AM - 12:00 PM": "Take a break and do something you enjoy",
            "12:00 PM - 1:00 PM": "Lunch break",
            "1:00 PM - 2:00 PM": "Work on a task"
        },
        "Afternoon": {
            "2:00 PM - 3:00 PM": "Take a break and do something you enjoy",
            "3:00 PM - 4:00 PM": "Work on a task",
            "4:00 PM - 5:00 PM": "Take a break and do something you enjoy",
            "5:00 PM - 6:00 PM": "Start winding down for the day"
        },
        "Evening": {
            "6:00 PM - 7:00 PM": "Dinner",
            "7:00 PM - 8:00 PM": "Spend time with family/friends",
            "8:00 PM - 9:00 PM": "Relax and unwind",
            "9:00 PM - 10:00 PM": "Get ready for bed"
        }
    }

    # Generate a daily schedule
    daily_schedule = {}
    for time, activity in schedule["Morning"].items():
        daily_schedule[time] = activity
    for time, activity in schedule["Mid-Morning"].items():
        daily_schedule[time] = activity
    for time, activity in schedule["Afternoon"].items():
        daily_schedule[time] = activity
    for time, activity in schedule["Evening"].items():
        daily_schedule[time] = activity

    # Add random tasks and breaks to the schedule
    for hour in range(6, 20):
        if random.random() < 0.3:
            daily_schedule[f"{hour}:00 AM"] = random.choice(tasks)
        if random.random() < 0.2:
            daily_schedule[f"{hour}:00 AM"] = random.choice(breaks)
        if random.random() < 0.1:
            daily_schedule[f"{hour}:00 AM"] = random.choice(leisure_activities)

    # Add leisure activities to the schedule
    for hour in range(6, 20):
        if random.random() < 0.5:
            daily_schedule[f"{hour}:00 AM"] = random.choice(leisure_activities)

    return daily_schedule

def print_schedule(schedule):
    for time, activity in schedule.items():
        print(f"{time}: {activity}")

def main():
    schedule = generate_schedule()
    print_schedule(schedule)

if __name__ == "__main__":
    main()