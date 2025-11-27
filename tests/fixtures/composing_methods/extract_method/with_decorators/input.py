"""Example code for extract-method with decorators."""


def log_call(func):
    """Custom decorator for logging method calls."""

    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)

    return wrapper


class Product:
    def __init__(self, name, base_price, tax_rate):
        self._name = name
        self._base_price = base_price
        self._tax_rate = tax_rate

    @property
    def display_info(self):
        """Get product display information."""
        # Calculate pricing information
        tax = self._base_price * self._tax_rate
        total = self._base_price + tax

        return f"{self._name}: ${self._base_price:.2f} + ${tax:.2f} tax = ${total:.2f} total"

    @log_call
    def apply_discount(self, discount_percent):
        """Apply a discount to the product."""
        # Calculate discount amount
        discount = self._base_price * (discount_percent / 100)
        new_price = self._base_price - discount

        self._base_price = new_price
        return new_price
