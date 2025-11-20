def calculate_total(order):
    base_price = order.quantity * order.item_price
    return base_price > 1000
