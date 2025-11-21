def calculate_total(order):
    total = (
        order.quantity * order.item_price
        - max(0, order.quantity - 500) * order.item_price * 0.05
        + min(order.quantity * order.item_price * 0.1, 100.0)
    )
    return total
