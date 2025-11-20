class Calculator:
    def calculate(self, amount):
        if amount > 100:
            amount -= 10
        if amount > 50:
            amount -= 5
        return amount
