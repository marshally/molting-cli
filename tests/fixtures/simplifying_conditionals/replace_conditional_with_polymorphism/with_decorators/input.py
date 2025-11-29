"""Expected output after replace conditional with polymorphism with decorators."""


class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type, monthly_salary, commission=0, bonus=0):
        self.type = employee_type
        self.monthly_salary = monthly_salary
        self.commission = commission
        self.bonus = bonus

    @property
    def pay_amount(self):
        if self.type == self.ENGINEER:
            return self.monthly_salary
        elif self.type == self.SALESMAN:
            return self.monthly_salary + self.commission
        elif self.type == self.MANAGER:
            return self.monthly_salary + self.bonus
        else:
            raise ValueError("Invalid employee type")
