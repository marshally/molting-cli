class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_telephone = TelephoneNumber(office_area_code, office_number)

    def get_telephone_number(self):
        return self.office_telephone.get_telephone_number()


class TelephoneNumber:
    def __init__(self, area_code, number):
        self.area_code = area_code
        self.number = number

    def get_telephone_number(self):
        return f"({self.area_code}) {self.number}"
