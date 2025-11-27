"""Expected output after inline-method with instance variables."""


class ShoppingCart:
    def __init__(self):
        self.items = []
        self.tax_rate = 0.08

    def get_total(self):
        """Get total price including tax."""
        total = 0
        for item in self.items:
            total += item.price
        return total * (1 + self.tax_rate)
