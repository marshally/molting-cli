"""Example code for inline-method with decorators."""


class ShoppingCart:
    def __init__(self, items):
        self._items = items

    @property
    def total(self):
        """Get the total price."""
        return self._get_base_total() * 1.1

    def _get_base_total(self):
        """Calculate base total without tax."""
        return sum(item.price for item in self._items)

    @property
    def item_count(self):
        """Get the number of items."""
        return len(self._items)
