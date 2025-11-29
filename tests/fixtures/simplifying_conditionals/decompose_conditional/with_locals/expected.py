"""Example code for decompose conditional with local variables."""


def process_order(order, customer_type, base_price):
    # Local variables used in the conditional
    discount = 0.0
    tax_rate = 0.08

    if is_premium_order(customer_type, order):
        discount = base_price * 0.15
        total = base_price - discount + (base_price * tax_rate)
    else:
        discount = base_price * 0.05
        total = base_price - discount + (base_price * tax_rate)

    return total


def is_premium_order(customer_type, order):
    return customer_type == "premium" and order.total > 1000
