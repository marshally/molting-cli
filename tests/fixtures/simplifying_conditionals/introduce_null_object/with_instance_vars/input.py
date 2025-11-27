"""Example code for introduce-null-object with instance variables."""


class OrderManager:
    def __init__(self, customer, discount_rate=0.1):
        self.customer = customer
        self.discount_rate = discount_rate
        self.tax_rate = 0.08

    def calculate_total(self, base_price):
        if self.customer is not None:
            total = base_price * (1 - self.discount_rate)
            total = total * (1 + self.tax_rate)
            return total
        else:
            return base_price * (1 + self.tax_rate)


class Customer:
    def __init__(self, name, tier="Standard"):
        self.name = name
        self.tier = tier


# Client code would check: if customer is not None
