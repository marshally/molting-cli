class Calculator:
    def calculate(self, amount):
        result = amount
        if result > 100:
            result -= 10
        if result > 50:
            result -= 5
        return result
