# DESCRIPTION: A class-based task manager for organizing and tracking tasks.
# --- GLADOS SKILL: skill_task_manager.py ---

import json
import uuid
import time
from datetime import timedelta


class TaskManager:
    def __init__(self):
        self.tasks = {}

    def add_task(self, name, description, duration):
        task_id = uuid.uuid4().hex
        self.tasks[task_id] = {
            "name": name,
            "description": description,
            "duration": duration,
            "start_time": int(time.time()),
        }
        return task_id

    def get_running_tasks(self):
        result = []
        for task_id, t in self.tasks.items():
            remaining = t["duration"] - (int(time.time()) - t["start_time"])
            if remaining > 0:
                result.append((task_id, t["name"], timedelta(seconds=remaining)))
        return result


def main():
    tm = TaskManager()
    # Demo: add one task and show running tasks
    tm.add_task("Sample task", "Added by GLaDOS", 60)
    running = tm.get_running_tasks()
    if running:
        for task_id, name, duration in running:
            print(f"Task: {name} (ID: {task_id[:8]}...) — remaining: {duration}")
    else:
        print("No running tasks.")


if __name__ == "__main__":
    main()
