"""Example code for rename-method with decorators."""


class Product:
    def __init__(self, name, price):
        self._name = name
        self._price = price

    @property
    def n(self):
        """Get product name."""
        return self._name

    @property
    def p(self):
        """Get product price."""
        return self._price

    @staticmethod
    def calc_disc(price, rate):
        """Calculate discount."""
        return price * rate

    @classmethod
    def cr_default(cls):
        """Create default product."""
        return cls("Default", 0.0)
