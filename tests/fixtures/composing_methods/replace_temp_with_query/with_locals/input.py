"""Example code for replace temp with query with local variables."""


class Invoice:
    def __init__(self, quantity, item_price, discount_rate):
        self.quantity = quantity
        self.item_price = item_price
        self.discount_rate = discount_rate

    def calculate_total(self):
        # Calculate base price with local variable
        base_price = self.quantity * self.item_price

        # Use base_price in multiple calculations
        discount = base_price * self.discount_rate
        tax = base_price * 0.1

        # Final calculation uses the temp multiple times
        total = base_price - discount + tax
        return total
