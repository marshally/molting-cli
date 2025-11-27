"""Example code for hide-method with decorators."""


def memoize(func):
    """Decorator to memoize results."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


class Calculator:
    def __init__(self):
        self.base_rate = 1.0

    @memoize
    def calculate_discount_rate(self):
        """Calculate the discount rate based on base rate."""
        return self.base_rate * 0.9

    def get_discounted_price(self, price):
        """Get price with discount applied."""
        return price * self.calculate_discount_rate()
