"""Example code for replace conditional with polymorphism with decorators."""


class Employee:
    def __init__(self, monthly_salary):
        self.monthly_salary = monthly_salary

    @property
    def pay_amount(self):
        raise NotImplementedError


class Engineer(Employee):
    @property
    def pay_amount(self):
        return self.monthly_salary


class Salesman(Employee):
    def __init__(self, monthly_salary, commission):
        super().__init__(monthly_salary)
        self.commission = commission

    @property
    def pay_amount(self):
        return self.monthly_salary + self.commission


class Manager(Employee):
    def __init__(self, monthly_salary, bonus):
        super().__init__(monthly_salary)
        self.bonus = bonus

    @property
    def pay_amount(self):
        return self.monthly_salary + self.bonus
