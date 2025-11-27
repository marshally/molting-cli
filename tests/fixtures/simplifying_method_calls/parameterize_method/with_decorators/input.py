"""Example code for parameterize-method with decorators."""


def track_changes(func):
    """Decorator to track salary changes."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


class Employee:
    def __init__(self, salary):
        self.salary = salary

    @track_changes
    def small_raise(self):
        self.salary *= 1.05

    @track_changes
    def large_raise(self):
        self.salary *= 1.10
