"""Example code for extract-class with multiple call sites."""


class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_area_code = office_area_code
        self.office_number = office_number

    def get_telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"

    def format_contact_info(self):
        return f"{self.name}: {self.get_telephone_number()}"

    def validate_phone(self):
        return len(self.office_area_code) == 3 and len(self.office_number) == 7


class Directory:
    def __init__(self):
        self.people = []

    def list_contacts(self):
        contacts = []
        for person in self.people:
            phone = f"({person.office_area_code}) {person.office_number}"
            contacts.append(f"{person.name}: {phone}")
        return contacts

    def find_by_area_code(self, area_code):
        results = []
        for person in self.people:
            if person.office_area_code == area_code:
                results.append(person)
        return results


class PhoneFormatter:
    def format_international(self, person):
        return f"+1 ({person.office_area_code}) {person.office_number}"

    def get_area_code(self, person):
        return person.office_area_code
