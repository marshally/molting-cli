"""Example code for inline-class with multiple call sites."""


class Person:
    def __init__(self, name):
        self.name = name
        self.office_telephone = TelephoneNumber()

    def get_telephone_number(self):
        return self.office_telephone.get_telephone_number()

    def update_area_code(self, code):
        self.office_telephone.area_code = code


class TelephoneNumber:
    def __init__(self):
        self.area_code = ""
        self.number = ""

    def get_telephone_number(self):
        return f"({self.area_code}) {self.number}"


class Directory:
    def __init__(self):
        self.people = []

    def list_phones(self):
        phones = []
        for person in self.people:
            phone = person.office_telephone.get_telephone_number()
            phones.append(f"{person.name}: {phone}")
        return phones

    def update_numbers(self, person, area_code, number):
        person.office_telephone.area_code = area_code
        person.office_telephone.number = number


class PhoneValidator:
    def is_valid(self, person):
        tel = person.office_telephone
        return len(tel.area_code) == 3 and len(tel.number) == 7

    def format_display(self, person):
        return person.office_telephone.get_telephone_number()
