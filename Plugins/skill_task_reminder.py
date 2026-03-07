# DESCRIPTION: A class to manage reminders of tasks to be performed on specific dates.
# --- GLADOS SKILL: skill_task_reminder.py ---

import datetime

class TaskReminder:
    def __init__(self, reminders=None):
        if reminders is None:
            self.reminders = []
        else:
            self.reminders = reminders

    def add_reminder(self, name, date):
        self.reminders.append({"name": name, "date": date})

    def view_reminders(self):
        for reminder in self.reminders:
            print(f"Reminder: {reminder['name']} - Date: {reminder['date']}")

def today():
    return datetime.date.today()

def main():
    reminder_app = TaskReminder()
    reminder_app.add_reminder("Meeting", today())
    reminder_app.add_reminder("Exam", (datetime.date.today() + datetime.timedelta(days=14)).strftime("%m/%d/%Y"))
    reminder_app.view_reminders()

if __name__ == "__main__":
    main()


Please note that in the `main` function, we do not handle any possible exceptions, like file corruption when reading or writing to a reminder file. For a real-world application, you should consider implementing that. Also, the reminders are stored in memory and lost when the script exits. To make it persistent, you should consider using a database or file-based storage.