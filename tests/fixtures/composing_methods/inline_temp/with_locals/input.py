"""Example code for inline temp with local variables."""


def calculate_price(order):
    # Calculate base price with temp variable
    base_price = order.quantity * order.item_price

    # Use the temp in multiple expressions with other locals
    discount_threshold = 1000
    shipping_rate = 0.1

    # Multiple uses of base_price with other locals
    if base_price > discount_threshold:
        discount = base_price * 0.05
    else:
        discount = 0

    shipping = base_price * shipping_rate
    total = base_price - discount + shipping

    return total
