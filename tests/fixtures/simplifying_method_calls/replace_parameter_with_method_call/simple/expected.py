class Order:
    def __init__(self, quantity, item_price):
        self.quantity = quantity
        self.item_price = item_price

    def get_price(self):
        base_price = self.quantity * self.item_price
        return self.discounted_price(base_price)

    def discounted_price(self, base_price):
        if self.get_discount_level() == 2:
            return base_price * 0.9
        return base_price * 0.95

    def get_discount_level(self):
        return 2 if self.quantity > 100 else 1
