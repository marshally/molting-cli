"""Example code for remove-parameter with multiple call sites."""


class Order:
    def __init__(self, base_price, quantity):
        self.base_price = base_price
        self.quantity = quantity

    def calculate_total(self, discount_code):
        # discount_code is no longer used
        return self.base_price * self.quantity


class ShoppingCart:
    def __init__(self):
        self.orders = []

    def add_order(self, order):
        self.orders.append(order)

    def get_cart_total(self):
        total = 0
        for order in self.orders:
            total += order.calculate_total(None)
        return total

    def print_receipt(self):
        for order in self.orders:
            amount = order.calculate_total("")
            print(f"Order: ${amount}")


def process_order(order):
    total = order.calculate_total("UNUSED")
    print(f"Processing order for ${total}")
    return total


def generate_invoice(orders):
    invoice_total = 0
    for order in orders:
        invoice_total += order.calculate_total("ignored")
    return invoice_total
