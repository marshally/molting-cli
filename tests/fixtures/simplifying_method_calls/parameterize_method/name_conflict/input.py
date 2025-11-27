"""Example code for parameterize method with name conflict."""


class Employee:
    def __init__(self, salary):
        self.salary = salary

    def five_percent_raise(self):
        self.salary *= 1.05

    def ten_percent_raise(self):
        self.salary *= 1.10

    def raise_salary(self, custom_percent):
        """This method already exists - should conflict."""
        self.salary *= 1 + custom_percent / 50  # Different implementation
