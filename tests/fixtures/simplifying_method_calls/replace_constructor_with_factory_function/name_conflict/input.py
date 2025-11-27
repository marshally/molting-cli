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
