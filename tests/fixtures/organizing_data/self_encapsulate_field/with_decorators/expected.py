"""Example code for self-encapsulate-field with decorators."""


class Range:
    def __init__(self, low, high):
        self._low = low
        self._high = high

    @property
    def width(self):
        """Calculate the width of the range."""
        return self.high - self.low

    @property
    def low(self):
        return self._low

    @low.setter
    def low(self, value):
        self._low = value

    @property
    def high(self):
        return self._high

    @high.setter
    def high(self, value):
        self._high = value

    @staticmethod
    def create_unit_range(value):
        """Create a range of width 1."""
        return Range(value, value + 1)

    def includes(self, arg):
        return arg >= self.low and arg <= self.high
