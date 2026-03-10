# DESCRIPTION: This script generates a personalized daily itinerary based on the user's schedule, appointments, and preferences to ensure they make the most of their time.
# --- AUTONOMOUSLY GENERATED SKILL ---

from datetime import datetime, timedelta

class Itinerary:
    def __init__(self, user_schedule, appointments, preferences):
        self.user_schedule = user_schedule
        self.appointments = appointments
        self.preferences = preferences

    def generate_itinerary(self):
        # Sort appointments by time
        self.appointments.sort(key=lambda x: x[0])

        # Initialize itinerary
        itinerary = []

        # Add morning routine
        itinerary.append(("Morning Routine", self.user_schedule["morning_routine"]))

        # Add appointments
        for appointment in self.appointments:
            start_time = appointment[0]
            end_time = appointment[1]
            duration = end_time - start_time
            if duration > timedelta(hours=1):
                itinerary.append((f"{appointment[2]}", start_time, end_time))
            else:
                itinerary.append((f"{appointment[2]}", start_time, start_time + timedelta(minutes=duration)))

        # Add evening routine
        itinerary.append(("Evening Routine", self.user_schedule["evening_routine"]))

        return itinerary

def main():
    user_schedule = {
        "morning_routine": "Exercise",
        "evening_routine": "Meditation"
    }

    appointments = [
        ("8:00 AM", "9:00 AM", "Breakfast"),
        ("9:30 AM", "11:30 AM", "Work"),
        ("12:00 PM", "1:00 PM", "Lunch"),
        ("2:00 PM", "4:00 PM", "Work"),
        ("5:00 PM", "6:00 PM", "Dinner"),
        ("7:00 PM", "8:00 PM", "Relaxation")
    ]

    preferences = {
        "work_hours": "9:30 AM - 4:00 PM",
        "meal_times": ["12:00 PM", "5:00 PM"]
    }

    user_schedule["work_hours"] = preferences["work_hours"]
    user_schedule["meal_times"] = preferences["meal_times"]

    itinerary = Itinerary(user_schedule, appointments, preferences)
    print(itinerary.generate_itinerary())

if __name__ == "__main__":
    main()