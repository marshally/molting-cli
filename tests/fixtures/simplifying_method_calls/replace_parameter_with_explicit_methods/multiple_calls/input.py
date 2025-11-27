"""Example code for replace-parameter-with-explicit-methods with multiple call sites."""


class Employee:
    HEIGHT = 0
    WIDTH = 1

    def __init__(self):
        self.height = 0
        self.width = 0

    def set_value(self, name, value):
        if name == "height":
            self.height = value
        elif name == "width":
            self.width = value


class EmployeeManager:
    def __init__(self):
        self.employees = []

    def create_employee(self, h, w):
        emp = Employee()
        emp.set_value("height", h)
        emp.set_value("width", w)
        self.employees.append(emp)

    def update_employee_dimensions(self, emp, new_height, new_width):
        emp.set_value("height", new_height)
        emp.set_value("width", new_width)


def initialize_employee(employee):
    employee.set_value("height", 180)
    employee.set_value("width", 60)


def adjust_employee_size(employee, adjustment):
    employee.set_value("height", employee.height + adjustment)
    employee.set_value("width", employee.width + adjustment)
