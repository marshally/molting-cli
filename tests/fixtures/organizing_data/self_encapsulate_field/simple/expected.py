class Range:
    def __init__(self, low, high):
        self._low = low
        self._high = high

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

    def includes(self, arg):
        return arg >= self.low and arg <= self.high
