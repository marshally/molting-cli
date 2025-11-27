class Contact:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.phone = None
        self.address = None

    def get_contact_info(self):
        return f"{self.name} <{self.email}>"


class Employee(Contact):
    def __init__(self, name, email, employee_id):
        super().__init__(name, email)
        self.employee_id = employee_id
        self.department = None
        self.hire_date = None

    def get_employee_summary(self):
        return f"ID: {self.employee_id}, {self.get_contact_info()}"
