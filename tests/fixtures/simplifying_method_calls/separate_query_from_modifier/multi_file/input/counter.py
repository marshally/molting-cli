"""Counter system for tracking events."""


class Counter:
    """A counter that tracks numeric values."""

    def __init__(self, initial_value=0):
        self._value = initial_value

    def increment_and_get(self):
        """Increment the counter and return the new value.

        This method both modifies state (increments) and returns a value (queries).

        Returns:
            The new value after incrementing
        """
        self._value += 1
        return self._value

    def reset(self):
        """Reset the counter to zero."""
        self._value = 0
