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
        return employee.monthly_salary


class Employee:
    ENGINEER = Engineer()
    SALESMAN = Salesman()
    MANAGER = Manager()

    def __init__(self, employee_type, monthly_salary=0, commission=0):
        self.type = employee_type
        self.monthly_salary = monthly_salary
        self.commission = commission

    def pay_amount(self):
        return self.type.pay_amount(self)
