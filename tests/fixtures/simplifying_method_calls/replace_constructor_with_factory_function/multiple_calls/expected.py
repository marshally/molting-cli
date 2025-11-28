"""Expected output after replace-constructor-with-factory-function with multiple call sites."""


class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type


def create_employee(employee_type):
    return Employee(employee_type)


class Department:
    def __init__(self):
        self.employees = []

    def hire_engineer(self):
        emp = create_employee(Employee.ENGINEER)
        self.employees.append(emp)
        return emp

    def hire_manager(self):
        emp = create_employee(Employee.MANAGER)
        self.employees.append(emp)
        return emp


def create_sales_team(size):
    team = []
    for i in range(size):
        team.append(create_employee(Employee.SALESMAN))
    return team


def onboard_employee(role_type):
    employee = create_employee(role_type)
    print(f"Onboarding employee of type {role_type}")
    return employee
