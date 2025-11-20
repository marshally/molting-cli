class Range:
    def __init__(self, low, high):
        self.low = low
        self.high = high

    def includes(self, arg):
        return arg >= self.low and arg <= self.high
