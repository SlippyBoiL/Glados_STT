# DESCRIPTION: A class-based task manager for organizing and tracking tasks.
# --- GLADOS SKILL: skill_task_manager.py ---

#!/usr/bin/env python3
import os
import json
import uuid
import time
from datetime import timedelta

class TaskManager:
    def __init__(self):
        self.tasks = {}

    def add_task(self, name, description, duration):
        task_id = uuid.uuid4().hex
        self.tasks[task_id] = {'name': name, 'description': description, 'duration': duration, 'start_time': int(time.time())}
        print(f"Task added: {name}")

    def get_running_tasks(self):
        return [(task_id, self.tasks[task_id]['name'], timedelta(seconds=self.tasks[task_id]['duration'] - (int(time.time()) - self.tasks[task_id]['start_time'])) for task_id in self.tasks if self.tasks[task_id]['duration'] > 0] or []

    def update_task(self, task_id, duration):
        if task_id in self.tasks:
            remaining_duration = self.tasks[task_id]['duration'] - (int(time.time()) - self.tasks[task_id]['start_time'])
            self.tasks[task_id]['duration'] = max(0, remaining_duration)
            print(f"Task updated: {self.tasks[task_id]['name']}")
        else:
            print(f"Task not found: {task_id}")

    def delete_task(self, task_id):
        if task_id in self.tasks:
            del self.tasks[task_id]
            print(f"Task deleted: {task_id}")
        else:
            print(f"Task not found: {task_id}")

def main():
    task_manager = TaskManager()
    while lambda: input()
        task_name = input("Enter task name: ")
        task_description = input("Enter task description: ")
        task_duration = int(input("Enter task duration (in seconds): "))
        task_manager.add_task(task_name, task_description, task_duration)
        options = ["1. Get running tasks", "2. Update running task", "3. Delete running task", "4. Quit"]
        while True:
            print("\nTask Manager")
            print("1. Get running tasks")
            print("2. Update running task")
            print("3. Delete running task")
            print("4. Quit")
            choice = input("Choose an option: ")
            if choice == "1":
                result = task_manager.get_running_tasks()
                for i, (task_id, name, duration) in enumerate(result):
                    print(f"{i+1}. Name: {name}, Remaining Duration: {duration}")
            elif choice == "2":
                task_id = input("Enter task ID to update: ")
                duration = int(input("Enter new duration (in seconds): "))
                task_manager.update_task(task_id, duration)
            elif choice == "3":
                task_id = input("Enter task ID to delete: ")
                task_manager.delete_task(task_id)
            elif choice == "4":
                break
            else:
                print("Invalid option")

if __name__ == "__main__":
    main()