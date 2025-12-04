"""Order class that should own the discount calculation."""


class Order:
    """Order class that is the natural home for discount calculations."""

    def __init__(self, base_price: float, quantity: int):
        self.base_price = base_price
        self.quantity = quantity

    def total_price(self):
        """Calculate total price without discount."""
        return self.base_price * self.quantity

    def calculate_discount(self, discount_rate):
        """Calculate discount for an order.

        This method uses order data more than customer data,
        so it should be moved to the Order class.
        """
        base_price = self.base_price
        quantity = self.quantity

        # The calculation primarily uses order data
        if quantity > 100:
            return base_price * quantity * discount_rate * 1.5
        else:
            return base_price * quantity * discount_rate
