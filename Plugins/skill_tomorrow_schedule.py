# DESCRIPTION: A simple tkinter GUI application used to schedule and add tasks for the next day.
# --- GLADOS SKILL: skill_tomorrow_schedule.py ---

# skill_tomorrow_schedule.py

import datetime
import pytz
import tkinter as tk
from tkinter import messagebox

class Schedule:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tomorrow Schedule")

        self.entry = tk.Entry(self.root, width=30)
        self.entry.pack(padx=10, pady=10)

        self.button = tk.Button(self.root, text="Add Task", command=self.add_task)
        self.button.pack(pady=10)

        self.schedule = tk.Text(self.root, height=10, width=30)
        self.schedule.pack(padx=10, pady=10)

    def add_task(self):
        self.task = self.entry.get()
        if not self.task:
            messagebox.showerror("Error", "Please enter a task name")
            return

        self.schedule.insert(tk.END, self.task + "\n")

        # Simulate saving schedule to local file
        with open("tomorrow_schedule.txt", "a") as f:
            f.write(self.task + "\n")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    schedule = Schedule()
    schedule.run()