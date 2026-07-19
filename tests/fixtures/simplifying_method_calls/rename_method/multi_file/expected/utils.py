"""Utility functions for order processing."""


def format_order_summary(order):
    """Format a summary of an order."""
    price = order.calculate_total_price()
    return f"Order total: ${price:.2f}"


def calculate_tax(order, rate=0.1):
    """Calculate tax for an order."""
    return order.calculate_total_price() * rate


def compare_orders(order1, order2):
    """Compare two orders by price."""
    return order1.calculate_total_price() - order2.calculate_total_price()
