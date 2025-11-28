"""Example code for inline-method with decorators."""


class ShoppingCart:
    def __init__(self, items):
        self._items = items

    @property
    def total(self):
        """Get the total price."""
        return sum(item.price for item in self._items) * 1.1

    @property
    def item_count(self):
        """Get the number of items."""
        return len(self._items)
