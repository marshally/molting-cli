class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary


def create_employee(name, salary):
    return Employee(name, salary)
