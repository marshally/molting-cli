"""Expected output after extract method with return value."""


class Calculator:
    def __init__(self, base_price, quantity):
        self.base_price = base_price
        self.quantity = quantity

    def compute(self):
        discount = self.apply_discount()
        total = self.base_price - discount

        return total

    def apply_discount(self):
        """Calculate the discount amount."""
        discount_rate = 0.05 if self.quantity > 100 else 0.02
        discount = self.base_price * discount_rate
        return discount
