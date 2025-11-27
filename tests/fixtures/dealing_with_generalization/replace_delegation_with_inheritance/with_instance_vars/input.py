class Contact:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.phone = None
        self.address = None

    def get_contact_info(self):
        return f"{self.name} <{self.email}>"


class Employee:
    def __init__(self, name, email, employee_id):
        self._contact = Contact(name, email)
        self.employee_id = employee_id
        self.department = None
        self.hire_date = None

    def get_name(self):
        return self._contact.name

    def set_name(self, name):
        self._contact.name = name

    def get_email(self):
        return self._contact.email

    def get_contact_info(self):
        return self._contact.get_contact_info()

    def get_employee_summary(self):
        return f"ID: {self.employee_id}, {self.get_contact_info()}"
