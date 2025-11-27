"""Expected output after consolidate-duplicate-conditional-fragments with multiple call sites."""


def process_order(is_special, price):
    if is_special:
        total = price * 0.95
    else:
        total = price * 0.98
    send_order()
    return total


def process_refund(is_vip, amount):
    if is_vip:
        refund = amount * 1.1
    else:
        refund = amount
    send_refund()
    return refund


def process_discount(has_coupon, base_price):
    if has_coupon:
        final = base_price * 0.8
    else:
        final = base_price
    apply_discount()
    return final


def send_order():
    pass


def send_refund():
    pass


def apply_discount():
    pass
