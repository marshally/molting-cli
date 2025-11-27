"""Example code for replace-temp-with-query with instance variables."""


class Product:
    def __init__(self, base_price, discount_rate, tax_rate):
        self.base_price = base_price
        self.discount_rate = discount_rate
        self.tax_rate = tax_rate

    def get_final_price(self):
        """Calculate final price with discount and tax."""
        if self.discounted_price() > 1000:
            return self.discounted_price() * 0.95
        return self.discounted_price() * (1 + self.tax_rate)
    def discounted_price(self):
        return self.base_price * (1 - self.discount_rate)
