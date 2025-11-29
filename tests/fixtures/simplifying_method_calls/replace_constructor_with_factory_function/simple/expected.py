class Employee:
    """Employee with type code that could benefit from factory construction."""

    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, name, employee_type):
        self.name = name
        self.employee_type = employee_type


def create_employee(name, employee_type):
    return Employee(name, employee_type)
