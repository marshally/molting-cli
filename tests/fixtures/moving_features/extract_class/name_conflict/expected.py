"""Example code for extract-class with name conflict."""


class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_area_code = office_area_code
        self.office_number = office_number

    def get_telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"


class TelephoneNumber:
    """This class already exists - creating a name conflict."""

    def __init__(self):
        self.area_code = "555"
