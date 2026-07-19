"""Person class with a phone_number attribute."""


class Person:
    """Person with a phone number.

    The PhoneNumber class is too simple and should be inlined.
    """

    def __init__(self, name: str, area_code: str, number: str):
        self.name = name
        self.area_code = area_code
        self.number = number

    def get_name(self):
        """Get person's name."""
        return self.name

    def get_phone_display(self):
        """Get formatted phone number for display."""
        return f"({self.area_code}) {self.number}"

    def get_area_code(self):
        """Get area code."""
        return self.area_code

    def get_number(self):
        """Get phone number."""
        return self.number
