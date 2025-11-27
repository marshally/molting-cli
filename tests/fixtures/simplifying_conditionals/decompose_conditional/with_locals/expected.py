"""Expected output after decompose conditional with local variables."""


def process_order(order, customer_type, base_price):
    # Local variables used in the conditional
    discount = 0.0
    tax_rate = 0.08

    if is_premium_order(customer_type, order):
        discount = base_price * 0.15
        total = calculate_total_with_discount(base_price, discount, tax_rate)
    else:
        discount = base_price * 0.05
        total = calculate_total_with_discount(base_price, discount, tax_rate)

    return total


def is_premium_order(customer_type, order):
    return customer_type == "premium" and order.total > 1000


def calculate_total_with_discount(base_price, discount, tax_rate):
    return base_price - discount + (base_price * tax_rate)
