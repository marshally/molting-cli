"""Example code for separate query from modifier with local variables."""


class TaskQueue:
    def __init__(self):
        self.tasks = []
        self.completed_count = 0

    def get_next(self):

        if len(self.tasks) > 0:
            return self.tasks[0]
        return None

    def process_next(self):

        if len(self.tasks) > 0:
            # Get the next task (query operation)
            next_task = self.tasks[0]

            # Remove it from the queue (modifier operation)
            self.tasks.pop(0)
            self.completed_count += 1

            # Additional processing with locals
            task_name = next_task.name if hasattr(next_task, 'name') else "Unknown"
            priority = next_task.priority if hasattr(next_task, 'priority') else 0

            print(f"Processing task: {task_name} (priority: {priority})")
