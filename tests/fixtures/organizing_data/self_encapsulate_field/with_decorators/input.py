"""Example code for self-encapsulate-field with decorators."""


class Range:
    def __init__(self, low, high):
        self.low = low
        self.high = high

    @property
    def width(self):
        """Calculate the width of the range."""
        return self.high - self.low

    @staticmethod
    def create_unit_range(value):
        """Create a range of width 1."""
        return Range(value, value + 1)

    def includes(self, arg):
        return arg >= self.low and arg <= self.high
