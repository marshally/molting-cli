"""Person class with unnecessary delegation to department.manager."""


class Person:
    """Person who belongs to a department.

    This class has too much delegation - get_manager() is just
    a simple pass-through that adds no value.
    """

    def __init__(self, name: str, department):
        self.name = name
        self.department = department

    def get_name(self):
        """Get person's name."""
        return self.name
