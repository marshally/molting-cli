class Calculator:
    def add(self, x, y):
        return self._compute(x) + self._compute(y)

    def multiply(self, x, y):
        return self._compute(x) * self._compute(y)

    def _compute(self, x):
        return x * 2
