"""Expected output after extract-class with decorators."""


class Employee:
    def __init__(self, name, street, city, state, zip_code):
        self.name = name
        self.address = Address(street, city, state, zip_code)

    @property
    def full_address(self):
        """Get the complete formatted address."""
        return self.address.full_address

    @property
    def mailing_label(self):
        """Get address formatted for mailing label."""
        return f"{self.name}\n{self.full_address}"

    def update_street(self, street):
        self.address.update_street(street)


class Address:
    def __init__(self, street, city, state, zip_code):
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code

    @property
    def full_address(self):
        return f"{self.street}\n{self.city}, {self.state} {self.zip_code}"

    def update_street(self, street):
        self.street = street
