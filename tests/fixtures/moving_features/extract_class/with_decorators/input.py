"""Example code for extract-class with decorators."""


class Employee:
    def __init__(self, name, street, city, state, zip_code):
        self.name = name
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code

    @property
    def full_address(self):
        """Get the complete formatted address."""
        return f"{self.street}\n{self.city}, {self.state} {self.zip_code}"

    @property
    def mailing_label(self):
        """Get address formatted for mailing label."""
        return f"{self.name}\n{self.full_address}"

    def update_street(self, street):
        self.street = street
