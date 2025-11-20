class Order:
    def __init__(self, quantity, item_price):
        self.quantity = quantity
        self.item_price = item_price

    def get_price(self):
        discount_factor = 0.98 if self.base_price() > 1000 else 0.95
        return self.base_price() * discount_factor

    def base_price(self):
        return self.quantity * self.item_price
