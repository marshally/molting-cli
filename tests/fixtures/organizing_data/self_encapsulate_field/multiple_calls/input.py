"""Example code for self-encapsulate-field with multiple call sites."""


class Range:
    def __init__(self, low, high):
        self.low = low
        self.high = high

    def includes(self, arg):
        return arg >= self.low and arg <= self.high

    def grow(self, amount):
        self.high = self.high + amount

    def width(self):
        return self.high - self.low


class RangeAnalyzer:
    def __init__(self, range_obj):
        self.range = range_obj

    def analyze(self):
        # Multiple accesses to range.low and range.high
        if self.range.low < 0:
            print(f"Range starts at negative value: {self.range.low}")

        if self.range.high > 100:
            print(f"Range extends beyond 100: {self.range.high}")

        mid = (self.range.low + self.range.high) / 2
        return mid
