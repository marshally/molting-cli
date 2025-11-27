"""Example code for add-parameter with decorators."""


def validate_input(func):
    """Decorator to validate input."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


class DataFormatter:
    def __init__(self, data):
        self._data = data

    @validate_input
    def format_value(self, value, uppercase=False):
        """Format a single value."""
        return f"[{value}]"
