"""Shopping cart that manages products."""

from product import Product


class ShoppingCart:
    """Shopping cart that calculates totals."""

    def __init__(self):
        self.items = []

    def add_item(self, product, quantity):
        """Add a product to the cart."""
        self.items.append((product, quantity))

    def get_total(self):
        """Calculate total price of all items in cart."""
        total = 0
        for product, quantity in self.items:
            total += product.price * quantity
        return total

    def get_most_expensive(self):
        """Find the most expensive item in the cart."""
        if not self.items:
            return None
        return max(self.items, key=lambda item: item[0].price)[0]

    def get_average_price(self):
        """Calculate average price of items in cart."""
        if not self.items:
            return 0
        total_price = sum(product.price for product, _ in self.items)
        return total_price / len(self.items)
