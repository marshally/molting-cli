"""Order class that should own the discount calculation."""


class Order:
    """Order class that is the natural home for discount calculations."""

    def __init__(self, base_price: float, quantity: int):
        self.base_price = base_price
        self.quantity = quantity

    def total_price(self):
        """Calculate total price without discount."""
        return self.base_price * self.quantity
