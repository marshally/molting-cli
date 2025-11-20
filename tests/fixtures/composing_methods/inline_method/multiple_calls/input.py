class Calculator:
    def simple_helper(self):
        return 5

    def add(self, a, b):
        return a + b + self.simple_helper()

    def multiply(self, a, b):
        return (a + b) * self.simple_helper()
