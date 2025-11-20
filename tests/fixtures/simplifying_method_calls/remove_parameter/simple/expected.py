class Order:
    def __init__(self, base_price, quantity):
        self.base_price = base_price
        self.quantity = quantity
        self.customer = None

    def calculate_total(self, customer):
        return self.base_price * self.quantity
