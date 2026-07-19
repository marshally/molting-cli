"""Product class with public price field."""


class Product:
    """A product with pricing information."""

    def __init__(self, name, price):
        self.name = name
        self._price = price

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        self._price = value

    def apply_discount(self, discount_percent):
        """Apply a discount to the product price."""
        self.price = self.price * (1 - discount_percent / 100)

    def get_info(self):
        """Get product information string."""
        return f"{self.name}: ${self.price:.2f}"
