class Employee:
    def get_annual_cost(self):
        return self.monthly_cost * 12


class Salesman(Employee):
    pass


class Engineer(Employee):
    pass
