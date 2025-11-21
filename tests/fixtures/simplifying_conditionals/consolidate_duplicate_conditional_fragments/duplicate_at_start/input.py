def process_order(is_special, price):
    if is_special:
        setup_order()
        total = price * 0.95
    else:
        setup_order()
        total = price * 0.98
    return total


def setup_order():
    pass
