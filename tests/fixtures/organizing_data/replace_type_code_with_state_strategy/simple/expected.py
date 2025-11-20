class EmployeeType:
    def pay_amount(self, employee):
        raise NotImplementedError


class Engineer(EmployeeType):
    def pay_amount(self, employee):
        return employee.monthly_salary


class Salesman(EmployeeType):
    def pay_amount(self, employee):
        return employee.monthly_salary + employee.commission


class Manager(EmployeeType):
    def pay_amount(self, employee):
        return employee.monthly_salary + employee.bonus


class Employee:
    def __init__(self, employee_type):
        self.type = employee_type
        self.monthly_salary = 0
        self.commission = 0
        self.bonus = 0

    def pay_amount(self):
        return self.type.pay_amount(self)
