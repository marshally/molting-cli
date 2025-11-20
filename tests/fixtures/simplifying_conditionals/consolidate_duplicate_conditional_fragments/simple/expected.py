def process_order(is_special, price):
    if is_special:
        total = price * 0.95
    else:
        total = price * 0.98
    send_order()
    return total


def send_order():
    pass
