"""Order processor that uses Order class."""

from order import Order


class OrderProcessor:
    def __init__(self):
        self.orders = []

    def add_order(self, order):
        self.orders.append(order)

    def calculate_total(self):
        """Calculate total of all orders."""
        total = 0
        for order in self.orders:
            total += order.get_price()
        return total

    def generate_invoice(self, order):
        """Generate an invoice for a single order."""
        price = order.get_price()
        return f"Invoice: ${price:.2f}"
