class Calculator:
    def add(self, x, y):
        return self.compute(x) + self.compute(y)

    def multiply(self, x, y):
        return self.compute(x) * self.compute(y)

    def compute(self, x):
        return x * 2
