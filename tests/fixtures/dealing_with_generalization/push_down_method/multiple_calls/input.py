"""Example code for push-down-method with multiple call sites."""


class Employee:
    def get_quota(self):
        return 100

    def calculate_target(self):
        quota = self.get_quota()
        return quota * 1.5

    def display_metrics(self):
        current_quota = self.get_quota()
        print(f"Quota: {current_quota}")


class Salesman(Employee):
    def get_commission(self):
        quota = self.get_quota()
        return quota * 0.05

    def print_goals(self):
        goal = self.get_quota()
        print(f"Sales goal: {goal}")


class Engineer(Employee):
    pass


class Manager(Employee):
    pass
