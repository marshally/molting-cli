"""Example code for replace constructor with factory function with name conflict."""


class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type


def create_employee(custom_param):
    """This function already exists - should conflict."""
    return Employee(custom_param * 2)


def create_employee(employee_type):
    if employee_type == "ENGINEER":
        return Employee(Employee.ENGINEER)
    elif employee_type == "SALESMAN":
        return Employee(Employee.SALESMAN)
    elif employee_type == "MANAGER":
        return Employee(Employee.MANAGER)
