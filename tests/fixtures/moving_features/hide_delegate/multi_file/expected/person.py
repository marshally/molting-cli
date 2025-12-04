"""Person class with department attribute."""


class Person:
    """Person who belongs to a department."""

    def __init__(self, name: str, department):
        self.name = name
        self.department = department

    def get_name(self):
        """Get person's name."""
        return self.name

    def get_manager(self):
        """Get person's manager.

        Hides the delegation to department.manager,
        following the Law of Demeter.
        """
        return self.department.manager
