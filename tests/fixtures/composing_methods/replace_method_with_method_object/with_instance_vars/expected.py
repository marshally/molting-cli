"""Example code for replace-method-with-method-object with instance variables."""


class Order:
    def __init__(self, items, customer):
        self.items = items
        self.customer = customer
        self.discount_rate = 0.1
        self.tax_rate = 0.08
        self.shipping_rate = 0.05

    def calculate_total(self):
        return Calculate_total(self).compute()


class Calculate_total:
    def __init__(self, account):
        self.account = account

    def compute(self):
        """Complex calculation using multiple instance variables."""
        # Calculate base price from items
        base_price = sum(item.price * item.quantity for item in self.account.items)

        # Apply customer-specific discount
        discount = base_price * self.account.discount_rate
        if self.account.customer.is_premium:
            discount *= 1.5

        # Calculate subtotal
        subtotal = base_price - discount

        # Add tax
        tax = subtotal * self.account.tax_rate

        # Add shipping
        shipping = base_price * self.account.shipping_rate

        # Final total
        total = subtotal + tax + shipping

        return total
