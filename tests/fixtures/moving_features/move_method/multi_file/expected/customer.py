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
        return order.calculate_discount(self.discount_rate)

    def get_info(self):
        """Get customer information."""
        return f"{self.name} (Discount: {self.discount_rate * 100}%)"
