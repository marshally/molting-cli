"""Example code for replace-parameter-with-method-call with multiple call sites."""


class Order:
    def __init__(self, quantity, item_price):
        self.quantity = quantity
        self.item_price = item_price

    def get_price(self):
        base_price = self.quantity * self.item_price
        discount_level = self.get_discount_level()
        return self.discounted_price(base_price, discount_level)

    def calculate_tax(self):
        base_price = self.quantity * self.item_price
        discount_level = self.get_discount_level()
        discounted = self.discounted_price(base_price, discount_level)
        return discounted * 0.1

    def discounted_price(self, base_price, discount_level):
        if discount_level == 2:
            return base_price * 0.9
        return base_price * 0.95

    def get_discount_level(self):
        return 2 if self.quantity > 100 else 1


class OrderProcessor:
    def calculate_shipping(self, order):
        base_price = order.quantity * order.item_price
        discount_level = order.get_discount_level()
        price = order.discounted_price(base_price, discount_level)
        return price * 0.05


def generate_invoice(order):
    base_price = order.quantity * order.item_price
    discount_level = order.get_discount_level()
    final_price = order.discounted_price(base_price, discount_level)
    return f"Invoice: ${final_price}"


def calculate_total_with_fees(order):
    base_price = order.quantity * order.item_price
    discount_level = order.get_discount_level()
    discounted = order.discounted_price(base_price, discount_level)
    return discounted + 5.00
