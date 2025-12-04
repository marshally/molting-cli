"""Small PhoneNumber class that should be inlined into Person."""


class PhoneNumber:
    """Simple phone number class.

    This class is too small and doesn't provide enough value
    to justify its existence. Should be inlined into Person.
    """

    def __init__(self, area_code: str, number: str):
        self.area_code = area_code
        self.number = number

    def get_area_code(self):
        """Get area code."""
        return self.area_code

    def get_number(self):
        """Get phone number."""
        return self.number
