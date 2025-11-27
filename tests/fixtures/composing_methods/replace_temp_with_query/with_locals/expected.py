"""Expected output after replace temp with query with local variables."""


class Invoice:
    def __init__(self, quantity, item_price, discount_rate):
        self.quantity = quantity
        self.item_price = item_price
        self.discount_rate = discount_rate

    def calculate_total(self):
        # Use base_price in multiple calculations
        discount = self.base_price() * self.discount_rate
        tax = self.base_price() * 0.1

        # Final calculation uses the temp multiple times
        total = self.base_price() - discount + tax
        return total

    def base_price(self):
        """Calculate base price."""
        return self.quantity * self.item_price
