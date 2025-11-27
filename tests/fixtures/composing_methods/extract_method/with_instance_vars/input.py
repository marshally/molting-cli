"""Example code for extract-method with instance variables."""


class Order:
    def __init__(self, items, customer):
        self.items = items
        self.customer = customer
        self.discount_rate = 0.0
        self.tax_rate = 0.1

    def calculate_total(self):
        """Calculate order total using instance variables."""
        # Calculate subtotal from items
        subtotal = 0.0
        for item in self.items:
            subtotal += item.price * item.quantity

        # Apply discount
        discount_amount = subtotal * self.discount_rate
        discounted_total = subtotal - discount_amount

        # Add tax
        tax_amount = discounted_total * self.tax_rate
        final_total = discounted_total + tax_amount

        return final_total
