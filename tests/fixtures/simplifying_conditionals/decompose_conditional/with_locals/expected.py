"""Example code for decompose conditional with local variables."""


def process_order(order, customer_type, base_price):
    # Local variables used in the conditional
    discount = 0.0
    tax_rate = 0.08

    if is_winter(customer_type, order):
        discount = base_price * 0.15
        total = winter_charge(base_price, discount, tax_rate)
    else:
        discount = base_price * 0.05
        total = summer_charge(base_price, discount, tax_rate)

    return total


def is_winter(customer_type, order):
    return customer_type == "premium" and order.total > 1000


def winter_charge(base_price, discount, tax_rate):
    return base_price - discount + (base_price * tax_rate)


def summer_charge(base_price, discount, tax_rate):
    return base_price - discount + (base_price * tax_rate)
