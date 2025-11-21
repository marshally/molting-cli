class Calculator:
    def calculate(self, x, y):
        return self._helper(x) + y

    def _helper(self, x):
        return x * 2
