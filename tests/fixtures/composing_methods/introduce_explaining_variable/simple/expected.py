def calculate_total(order):
    base_price = order.quantity * order.item_price
    quantity_discount = max(0, order.quantity - 500) * order.item_price * 0.05
    shipping = min(order.quantity * order.item_price * 0.1, 100.0)
    return base_price - quantity_discount + shipping
