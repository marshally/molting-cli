"""Person class with a phone_number attribute."""

from phone_number import PhoneNumber


class Person:
    """Person with a phone number.

    The PhoneNumber class is too simple and should be inlined.
    """

    def __init__(self, name: str, area_code: str, number: str):
        self.name = name
        self.phone_number = PhoneNumber(area_code, number)

    def get_name(self):
        """Get person's name."""
        return self.name

    def get_phone_display(self):
        """Get formatted phone number for display."""
        return f"({self.phone_number.area_code}) {self.phone_number.number}"
