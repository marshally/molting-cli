class Person:
    def __init__(self, name):
        self.name = name
        self.office_area_code = ""
        self.office_number = ""

    def get_telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"
