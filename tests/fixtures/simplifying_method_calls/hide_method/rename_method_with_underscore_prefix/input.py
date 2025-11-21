class Calculator:
    def calculate(self, x, y):
        return self.helper(x) + y

    def helper(self, x):
        return x * 2
