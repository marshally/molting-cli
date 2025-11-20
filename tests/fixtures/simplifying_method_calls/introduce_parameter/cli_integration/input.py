class Calculator:
    def compute(self, amount):
        return amount * 1.1

    def process(self):
        result1 = self.compute(100)
        result2 = self.compute(200)
        return result1 + result2


def calculate_with_calculator():
    calc = Calculator()
    return calc.compute(500)
