class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type


def create_employee(*args, **kwds):
    return Employee(*args, **kwds)
