"""Counter system for tracking events."""


class Counter:
    """A counter that tracks numeric values."""

    def __init__(self, initial_value=0):
        self._value = initial_value

    def increment(self):
        self._value += 1

    def get_value(self):
        return self._value

    def reset(self):
        """Reset the counter to zero."""
        self._value = 0
