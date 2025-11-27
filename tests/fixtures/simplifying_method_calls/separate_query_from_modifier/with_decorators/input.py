"""Example code for separate-query-from-modifier with decorators."""


def synchronized(func):
    """Decorator for thread synchronization."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


class TaskQueue:
    def __init__(self):
        self.tasks = []

    @synchronized
    def get_and_remove_next(self):
        """Get the next task and remove it from the queue."""
        if len(self.tasks) > 0:
            task = self.tasks[0]
            self.tasks.pop(0)
            return task
        return None
