"""Example code for replace-constructor-with-factory-function with multiple call sites."""


class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type


class Department:
    def __init__(self):
        self.employees = []

    def hire_engineer(self):
        emp = Employee(Employee.ENGINEER)
        self.employees.append(emp)
        return emp

    def hire_manager(self):
        emp = Employee(Employee.MANAGER)
        self.employees.append(emp)
        return emp


def create_sales_team(size):
    team = []
    for i in range(size):
        team.append(Employee(Employee.SALESMAN))
    return team


def onboard_employee(role_type):
    employee = Employee(role_type)
    print(f"Onboarding employee of type {role_type}")
    return employee


def create_employee(employee_type):
    if employee_type == "ENGINEER":
        return Employee(Employee.ENGINEER)
    elif employee_type == "SALESMAN":
        return Employee(Employee.SALESMAN)
    elif employee_type == "MANAGER":
        return Employee(Employee.MANAGER)
