class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type


def create_employee(employee_type):
    if employee_type == "ENGINEER":
        return Employee(Employee.ENGINEER)
    elif employee_type == "SALESMAN":
        return Employee(Employee.SALESMAN)
    elif employee_type == "MANAGER":
        return Employee(Employee.MANAGER)
