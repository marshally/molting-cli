"""Example code for pull-up-field with instance variables."""


class Employee:
    def __init__(self, id, department):
        self.employee_id = id
        self.department = department


class Salesman(Employee):
    def __init__(self, id, department, name, region):
        super().__init__(id, department)
        self.name = name
        self.region = region
        self.commission_rate = 0.1

    def calculate_commission(self, sales):
        return sales * self.commission_rate


class Engineer(Employee):
    def __init__(self, id, department, name, specialty):
        super().__init__(id, department)
        self.name = name
        self.specialty = specialty
        self.certifications = []

    def add_certification(self, cert):
        self.certifications.append(cert)
