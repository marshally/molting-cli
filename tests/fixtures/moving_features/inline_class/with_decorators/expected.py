"""Example code for inline-class with decorators."""


class Employee:
    def __init__(self, name):
        self.name = name
        self.street = ""
        self.city = ""
        self.state = ""
        self.zip_code = ""

    @property
    def full_address(self):
        """Get the complete formatted address."""
        return f"{self.street}\n{self.city}, {self.state} {self.zip_code}"

    def update_street(self, street):
        self.street = street
