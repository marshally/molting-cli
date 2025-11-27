"""Example code for inline-class with name conflict."""


class Person:
    def __init__(self, name):
        self.name = name
        self.office_telephone = TelephoneNumber()

    def get_telephone_number(self):
        """This method already exists in Person - will conflict with TelephoneNumber method."""
        return "existing implementation"


class TelephoneNumber:
    def __init__(self):
        self.area_code = ""
        self.number = ""

    def get_telephone_number(self):
        """This method will conflict with Person's method when inlined."""
        return f"({self.area_code}) {self.number}"
