"""Expected output after separate query from modifier with local variables."""


class TaskQueue:
    def __init__(self):
        self.tasks = []
        self.completed_count = 0

    def get_next(self):
        """Get the next task without modifying state (query)."""
        if len(self.tasks) > 0:
            return self.tasks[0]
        return None

    def process_next(self):
        """Process and remove the next task (modifier)."""
        if len(self.tasks) > 0:
            # Get the task for processing
            next_task = self.tasks[0]

            # Remove it from the queue
            self.tasks.pop(0)
            self.completed_count += 1

            # Additional processing with locals
            task_name = next_task.name if hasattr(next_task, 'name') else "Unknown"
            priority = next_task.priority if hasattr(next_task, 'priority') else 0

            print(f"Processing task: {task_name} (priority: {priority})")
