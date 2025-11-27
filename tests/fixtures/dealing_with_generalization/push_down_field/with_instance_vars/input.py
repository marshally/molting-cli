class Employee:
    def __init__(self, name, department):
        self.name = name
        self.department = department
        self.commission_rate = 0.0

    def get_info(self):
        return f"{self.name} - {self.department}"


class Salesman(Employee):
    def __init__(self, name, department):
        super().__init__(name, department)
        self.region = "North"

    def calculate_commission(self, sales):
        return sales * self.commission_rate


class Engineer(Employee):
    def __init__(self, name, department):
        super().__init__(name, department)
        self.certifications = []
