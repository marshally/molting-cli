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
    def get_next(self):
        if len(self.tasks) > 0:
            return self.tasks[0]
        return None

    @synchronized
    def remove_next(self):
        if len(self.tasks) > 0:
            self.tasks.pop(0)
