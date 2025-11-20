class Contact:
    def __init__(self, name, phone, email):
        self.name = name
        self.phone = phone
        self.email = email

    def get_contact_info(self, include_email=False):
        result = f"{self.name}\n{self.phone}"
        if include_email:
            result += f"\n{self.email}"
        return result
