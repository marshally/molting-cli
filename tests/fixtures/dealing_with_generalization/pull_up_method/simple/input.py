class Employee:
    def __init__(self, monthly_cost):
        self.monthly_cost = monthly_cost


class Salesman(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12


class Engineer(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12
