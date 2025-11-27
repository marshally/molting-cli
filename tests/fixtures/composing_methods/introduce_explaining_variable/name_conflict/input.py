"""Example code for introduce explaining variable with name conflict."""


def calculate_total(order):
    base_price = 1000  # This variable already exists - should cause conflict
    return (
        order.quantity * order.item_price
        - max(0, order.quantity - 500) * order.item_price * 0.05
        + min(order.quantity * order.item_price * 0.1, 100.0)
    ) + base_price
