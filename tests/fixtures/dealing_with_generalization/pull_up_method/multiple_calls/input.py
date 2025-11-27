"""Example code for pull-up-method with multiple call sites."""


class Employee:
    pass


class Salesman(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12

    def calculate_commission(self):
        base = self.get_annual_cost()
        return base * 0.05

    def display_summary(self):
        annual = self.get_annual_cost()
        print(f"Annual cost: ${annual}")


class Engineer(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12

    def calculate_budget(self):
        annual = self.get_annual_cost()
        return annual * 1.2

    def print_report(self):
        cost = self.get_annual_cost()
        print(f"Engineer cost: ${cost}")


class Manager(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12

    def calculate_team_budget(self):
        my_cost = self.get_annual_cost()
        return my_cost + self.team_budget

    def show_expenses(self):
        total = self.get_annual_cost()
        print(f"Manager expenses: ${total}")
