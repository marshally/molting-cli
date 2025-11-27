"""Example code for replace parameter with explicit methods with name conflict."""


class Employee:
    HEIGHT = 0
    WIDTH = 1

    def __init__(self):
        self.height = 0
        self.width = 0

    def set_height(self, value):
        self.height = value

    def set_width(self, value):
        self.width = value

    def set_height(self, custom_value):
        """This method already exists - should conflict."""
        self.height = custom_value * 2  # Different implementation
