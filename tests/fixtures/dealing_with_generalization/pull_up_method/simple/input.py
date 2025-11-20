class Employee:
    pass


class Salesman(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12


class Engineer(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12
