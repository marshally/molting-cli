class Employee:
    def __init__(self, id, department, name):
        self.employee_id = id
        self.department = department
        self.name = name


class Salesman(Employee):
    def __init__(self, id, department, name, region):
        super().__init__(id, department, name)
        self.region = region
        self.commission_rate = 0.1

    def calculate_commission(self, sales):
        return sales * self.commission_rate


class Engineer(Employee):
    def __init__(self, id, department, name, specialty):
        super().__init__(id, department, name)
        self.specialty = specialty
        self.certifications = []

    def add_certification(self, cert):
        self.certifications.append(cert)
