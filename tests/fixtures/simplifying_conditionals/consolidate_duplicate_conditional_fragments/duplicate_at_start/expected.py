def process_order(is_special, price):
    setup_order()
    if is_special:
        total = price * 0.95
    else:
        total = price * 0.98
    return total


def setup_order():
    pass
