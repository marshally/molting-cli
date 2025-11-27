"""Expected output after replace-parameter-with-explicit-methods with multiple call sites."""


class Employee:
    HEIGHT = 0
    WIDTH = 1

    def __init__(self):
        self.height = 0
        self.width = 0

    def set_height(self, value):
        self.height = value

    def set_width(self, value):
        self.width = value


class EmployeeManager:
    def __init__(self):
        self.employees = []

    def create_employee(self, h, w):
        emp = Employee()
        emp.set_height(h)
        emp.set_width(w)
        self.employees.append(emp)

    def update_employee_dimensions(self, emp, new_height, new_width):
        emp.set_height(new_height)
        emp.set_width(new_width)


def initialize_employee(employee):
    employee.set_height(180)
    employee.set_width(60)


def adjust_employee_size(employee, adjustment):
    employee.set_height(employee.height + adjustment)
    employee.set_width(employee.width + adjustment)
