"""Expected output after add-parameter with multiple call sites."""


class Contact:
    def __init__(self, name, phone):
        self.name = name
        self.phone = phone
        self.email = f"{name.lower()}@example.com"

    def get_contact_info(self, include_email=False):
        if include_email:
            return f"{self.name}: {self.phone} ({self.email})"
        return f"{self.name}: {self.phone}"


class ContactManager:
    def __init__(self):
        self.contacts = []

    def add_contact(self, contact):
        self.contacts.append(contact)

    def print_all_contacts(self):
        for contact in self.contacts:
            print(contact.get_contact_info())

    def export_contacts(self):
        result = []
        for contact in self.contacts:
            result.append(contact.get_contact_info())
        return "\n".join(result)


def display_contact(contact):
    info = contact.get_contact_info()
    print(f"Contact: {info}")


def format_contact_list(contacts):
    formatted = []
    for contact in contacts:
        formatted.append(f"- {contact.get_contact_info()}")
    return "\n".join(formatted)
