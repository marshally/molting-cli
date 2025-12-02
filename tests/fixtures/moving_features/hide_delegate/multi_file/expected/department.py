"""Department class with manager attribute."""


class Department:
    """Department with a manager."""

    def __init__(self, name: str, manager):
        self.name = name
        self.manager = manager

    def get_name(self):
        """Get department name."""
        return self.name
