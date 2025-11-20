class Order:
    def __init__(self, quantity, item_price):
        self.quantity = quantity
        self.item_price = item_price

    def get_price(self):
        base_price = self.quantity * self.item_price
        discount_level = self.get_discount_level()
        return self.discounted_price(base_price, discount_level)

    def discounted_price(self, base_price, discount_level):
        if discount_level == 2:
            return base_price * 0.9
        return base_price * 0.95

    def get_discount_level(self):
        return 2 if self.quantity > 100 else 1
