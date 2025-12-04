"""Person class with phone-related fields that should be extracted."""


class Person:
    """Person with embedded phone number data.

    The phone-related fields (area_code, number, extension)
    should be extracted into a PhoneNumber class.
    """

    def __init__(self, name: str, area_code: str, number: str, extension: str = ""):
        self.name = name
        self.phone_number = PhoneNumber(area_code, number, extension)

    def get_name(self):
        """Get person's name."""
        return self.name

    def get_phone_display(self):
        return self.phone_number.get_display()

    def get_area_code(self):
        return self.phone_number.get_area_code()

    def get_number(self):
        return self.phone_number.get_number()


class PhoneNumber:
    def __init__(self, area_code: str, number: str, extension: str = ""):
        self.area_code = area_code
        self.number = number
        self.extension = extension

    def get_display(self):
        """Get formatted phone number for display."""
        if self.extension:
            return f"({self.area_code}) {self.number} x{self.extension}"
        else:
            return f"({self.area_code}) {self.number}"

    def get_area_code(self):
        """Get area code."""
        return self.area_code

    def get_number(self):
        """Get phone number."""
        return self.number
