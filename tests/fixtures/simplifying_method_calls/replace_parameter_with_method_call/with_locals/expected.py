"""Example code for replace parameter with method call with local variables."""


class ShoppingCart:
    def __init__(self, items, customer_tier):
        self.items = items
        self.customer_tier = customer_tier

    def calculate_total(self):
        """Calculate total with local variables for shipping and tax."""
        subtotal = sum(item.price for item in self.items)

        # Store shipping cost in a local variable
        shipping_cost = self.get_shipping_cost()

        # Store tax rate in a local variable
        tax_rate = self.get_tax_rate()

        # Additional local processing
        pre_tax = subtotal + shipping_cost
        tax_amount = pre_tax * tax_rate

        # Pass locals as parameters instead of calling methods
        return self.apply_charges(subtotal, shipping_cost, tax_rate)

    def apply_charges(self, subtotal, tax_rate):
        """Apply shipping and tax charges."""
        pre_tax = subtotal + self.get_shipping()
        tax_amount = pre_tax * tax_rate
        total = pre_tax + tax_amount
        return round(total, 2)

    def get_shipping_cost(self):
        """Calculate shipping based on customer tier."""
        if self.customer_tier == "premium":
            return 0.0
        return 5.99

    def get_tax_rate(self):
        """Get applicable tax rate."""
        return 0.08
