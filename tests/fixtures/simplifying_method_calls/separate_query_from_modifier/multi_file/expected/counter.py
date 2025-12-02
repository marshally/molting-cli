"""Counter system for tracking events."""


class Counter:
    """A counter that tracks numeric values."""

    def __init__(self, initial_value=0):
        self._value = initial_value

    def increment(self):
        """Increment the counter.

        This method only modifies state without returning a value.
        """
        self._value += 1

    def get_value(self):
        """Get the current counter value.

        This method only queries state without modifying it.

        Returns:
            The current value
        """
        return self._value

    def reset(self):
        """Reset the counter to zero."""
        self._value = 0
