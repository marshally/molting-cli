"""Checkout module that calls customer.calculate_discount."""

from customer import Customer
from order import Order


def process_checkout(customer: Customer, order: Order):
    """Process a checkout with discount calculation.

    This is a call site that needs to be updated when
    calculate_discount moves to Order.
    """
    discount = customer.calculate_discount(order)
    total = order.total_price()
    final_price = total - discount

    print(f"Customer: {customer.get_info()}")
    print(f"Total: ${total:.2f}")
    print(f"Discount: ${discount:.2f}")
    print(f"Final Price: ${final_price:.2f}")

    return final_price


def calculate_savings(customer: Customer, order: Order):
    """Calculate how much customer saves with discount."""
    discount = customer.calculate_discount(order)
    return discount
