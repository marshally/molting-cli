class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary


def create_employee(name, salary):
    return Employee(name, salary)


def create_employee(custom_param):
    """This function already exists - should conflict."""
    return create_employee(custom_param, custom_param * 1000)
