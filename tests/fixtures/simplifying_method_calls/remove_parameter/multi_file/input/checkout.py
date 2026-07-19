from order import Order


def process_checkout(items, qty, unit_price):
    order = Order(items)
    total = order.calculate_total(qty, unit_price, None)
    print(f"Order total: ${total:.2f}")
    return total


def quick_checkout(items):
    order = Order(items)
    return order.calculate_total(1, 10.00, None)
