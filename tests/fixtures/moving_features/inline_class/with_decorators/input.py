"""Example code for inline-class with decorators."""


class Employee:
    def __init__(self, name):
        self.name = name
        self.address = Address()

    @property
    def full_address(self):
        return self.address.full_address

    def update_street(self, street):
        self.address.update_street(street)


class Address:
    def __init__(self):
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
