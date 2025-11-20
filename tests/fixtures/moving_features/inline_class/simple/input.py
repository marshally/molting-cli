class Person:
    def __init__(self, name):
        self.name = name
        self.office_telephone = TelephoneNumber()

    def get_telephone_number(self):
        return self.office_telephone.get_telephone_number()


class TelephoneNumber:
    def __init__(self):
        self.area_code = ""
        self.number = ""

    def get_telephone_number(self):
        return f"({self.area_code}) {self.number}"
