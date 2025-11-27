"""Expected output after extract-class with multiple call sites."""


class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_telephone = TelephoneNumber(office_area_code, office_number)

    def get_telephone_number(self):
        return self.office_telephone.get_telephone_number()

    def format_contact_info(self):
        return f"{self.name}: {self.get_telephone_number()}"

    def validate_phone(self):
        return len(self.office_telephone.area_code) == 3 and len(self.office_telephone.number) == 7


class TelephoneNumber:
    def __init__(self, area_code, number):
        self.area_code = area_code
        self.number = number

    def get_telephone_number(self):
        return f"({self.area_code}) {self.number}"


class Directory:
    def __init__(self):
        self.people = []

    def list_contacts(self):
        contacts = []
        for person in self.people:
            phone = f"({person.office_telephone.area_code}) {person.office_telephone.number}"
            contacts.append(f"{person.name}: {phone}")
        return contacts

    def find_by_area_code(self, area_code):
        results = []
        for person in self.people:
            if person.office_telephone.area_code == area_code:
                results.append(person)
        return results


class PhoneFormatter:
    def format_international(self, person):
        return f"+1 ({person.office_telephone.area_code}) {person.office_telephone.number}"

    def get_area_code(self, person):
        return person.office_telephone.area_code
