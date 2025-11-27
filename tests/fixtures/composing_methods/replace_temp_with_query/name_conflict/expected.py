"""Example code for replace temp with query with name conflict."""


class Order:
    def __init__(self, quantity, item_price):
        self.quantity = quantity
        self.item_price = item_price

    def get_price(self):
        base_price = self.quantity * self.item_price
        discount_factor = 0.98 if base_price > 1000 else 0.95
        return base_price * discount_factor

    def base_price(self):
        """This method already exists - should cause conflict."""
        return 500
