"""Example code for inline temp with local variables."""


def calculate_price(order):
    # Use the temp in multiple expressions with other locals
    discount_threshold = 1000
    shipping_rate = 0.1

    # Multiple uses of base_price with other locals
    if order.quantity * order.item_price > discount_threshold:
        discount = order.quantity * order.item_price * 0.05
    else:
        discount = 0

    shipping = order.quantity * order.item_price * shipping_rate
    total = order.quantity * order.item_price - discount + shipping

    return total
