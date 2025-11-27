"""Example code for introduce-local-extension with decorators."""


class EnhancedList(list):
    @property
    def is_empty(self):
        """Check if the list is empty."""
        return len(self) == 0

    @property
    def sum_value(self):
        """Calculate the sum of all numeric values."""
        return sum(self)

    @property
    def first(self):
        """Get the first item, or None if empty."""
        return self[0] if not self.is_empty else None


# Client code
# items = EnhancedList([1, 2, 3])
# if items.is_empty:
#     print("Empty")
# total = items.sum_value
