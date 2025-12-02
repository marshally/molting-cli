"""Person class with department attribute."""


class Person:
    """Person who belongs to a department."""

    def __init__(self, name: str, department):
        self.name = name
        self.department = department

    def get_name(self):
        """Get person's name."""
        return self.name
