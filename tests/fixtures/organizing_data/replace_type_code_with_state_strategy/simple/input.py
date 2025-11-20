class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type
        self.monthly_salary = 0
        self.commission = 0
        self.bonus = 0

    def pay_amount(self):
        if self.type == self.ENGINEER:
            return self.monthly_salary
        elif self.type == self.SALESMAN:
            return self.monthly_salary + self.commission
        elif self.type == self.MANAGER:
            return self.monthly_salary + self.bonus
