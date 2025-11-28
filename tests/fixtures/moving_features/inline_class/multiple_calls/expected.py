"""Example code for inline-class with multiple call sites."""


class Person:
    def __init__(self, name):
        self.name = name
        self.office_area_code = ""
        self.office_number = ""

    def get_telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"

    def update_area_code(self, code):
        self.office_area_code = code


class Directory:
    def __init__(self):
        self.people = []

    def list_phones(self):
        phones = []
        for person in self.people:
            phone = person.get_telephone_number()
            phones.append(f"{person.name}: {phone}")
        return phones

    def update_numbers(self, person, area_code, number):
        person.office_area_code = area_code
        person.office_number = number


class PhoneValidator:
    def is_valid(self, person):
        return len(person.office_area_code) == 3 and len(person.office_number) == 7

    def format_display(self, person):
        return person.get_telephone_number()
