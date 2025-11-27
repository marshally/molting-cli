"""Example code for inline-method with instance variables."""


class ShoppingCart:
    def __init__(self):
        self.items = []
        self.tax_rate = 0.08

    def get_total(self):
        """Get total price including tax."""
        return self.get_subtotal() * (1 + self.tax_rate)

    def get_subtotal(self):
        """Get subtotal from items."""
        total = 0
        for item in self.items:
            total += item.price
        return total
