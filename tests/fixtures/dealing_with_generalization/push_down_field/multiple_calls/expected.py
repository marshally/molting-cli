"""Example code for push-down-field with multiple call sites."""


class Employee:
    def __init__(self):
        self.base_salary = 50000

    def calculate_target(self):
        return self.quota * 1.5

    def display_info(self):
        print(f"Quota: {self.quota}")

    def annual_metrics(self):
        yearly_quota = self.quota * 12
        return yearly_quota


class Salesman(Employee):
    def __init__(self):
        super().__init__()
        self.quota = 100

    def get_commission(self):
        return self.quota * 0.05

    def print_goals(self):
        print(f"Sales quota: {self.quota}")

    def monthly_target(self):
        return self.quota + 20


class Engineer(Employee):
    pass


class Manager(Employee):
    pass
