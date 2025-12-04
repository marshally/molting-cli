"""Order class with method to be renamed."""


class Order:
    def __init__(self, quantity, item_price):
        self.quantity = quantity
        self.item_price = item_price

    def get_price(self):
        """Get the total price for this order."""
        return self.quantity * self.item_price

    def apply_discount(self, rate):
        """Apply a discount to the order."""
        price = self.get_price()
        return price * (1 - rate)
