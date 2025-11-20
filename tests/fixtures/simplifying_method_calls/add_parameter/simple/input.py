class Contact:
    def __init__(self, name, phone, email):
        self.name = name
        self.phone = phone
        self.email = email

    def get_contact_info(self):
        return f"{self.name}\n{self.phone}"
