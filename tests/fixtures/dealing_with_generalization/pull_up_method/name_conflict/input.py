"""Example code for pull-up-method with name conflict."""


class Employee:
    def get_annual_cost(self):
        # Method already exists in parent with different implementation
        return 10000


class Salesman(Employee):
    def get_annual_cost(self):
        # Trying to pull up this method would conflict
        return 50000


class Engineer(Employee):
    def get_annual_cost(self):
        # Trying to pull up this method would conflict
        return 50000
