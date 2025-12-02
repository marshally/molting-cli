"""Customer class that should delegate discount calculation to Order."""


class Customer:
    """Customer with a method that really belongs on Order."""

    def __init__(self, name: str, discount_rate: float):
        self.name = name
        self.discount_rate = discount_rate

    def calculate_discount(self, order):
        """Calculate discount for an order.

        This method uses order data more than customer data,
        so it should be moved to the Order class.
        """
        base_price = order.base_price
        quantity = order.quantity

        # The calculation primarily uses order data
        if quantity > 100:
            return base_price * quantity * self.discount_rate * 1.5
        else:
            return base_price * quantity * self.discount_rate

    def get_info(self):
        """Get customer information."""
        return f"{self.name} (Discount: {self.discount_rate * 100}%)"
