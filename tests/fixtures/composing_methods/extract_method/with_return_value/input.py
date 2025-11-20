"""Example code for extract method with return value."""


class Calculator:
    def __init__(self, base_price, quantity):
        self.base_price = base_price
        self.quantity = quantity

    def compute(self):
        # Calculate discount
        discount_rate = 0.05 if self.quantity > 100 else 0.02
        discount = self.base_price * discount_rate
        total = self.base_price - discount

        return total
