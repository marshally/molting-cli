class ShoppingCart:
    def __init__(self):
        self.items = []
        self.tax_rate = 0.08
        self.discount = 0.0

    def calc_amt(self):
        """Calculate total amount with tax and discount."""
        subtotal = sum(item.price for item in self.items)
        discounted = subtotal - (subtotal * self.discount)
        total = discounted + (discounted * self.tax_rate)
        return total

    def apply_promo(self, discount_percentage):
        """Apply promotional discount."""
        self.discount = discount_percentage
        return self.calc_amt()
