class Order:
    def __init__(self, base_price, quantity):
        self.base_price = base_price
        self.quantity = quantity
        self.customer = None

    def calculate_total(self, customer, discount_code):
        # discount_code is never used
        return self.base_price * self.quantity
