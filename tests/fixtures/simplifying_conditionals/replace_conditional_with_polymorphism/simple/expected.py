class Employee:
    def __init__(self, monthly_salary):
        self.monthly_salary = monthly_salary

    def pay_amount(self):
        raise NotImplementedError


class Engineer(Employee):
    def pay_amount(self):
        return self.monthly_salary


class Salesman(Employee):
    def __init__(self, monthly_salary, commission):
        super().__init__(monthly_salary)
        self.commission = commission

    def pay_amount(self):
        return self.monthly_salary + self.commission


class Manager(Employee):
    def __init__(self, monthly_salary, bonus):
        super().__init__(monthly_salary)
        self.bonus = bonus

    def pay_amount(self):
        return self.monthly_salary + self.bonus
