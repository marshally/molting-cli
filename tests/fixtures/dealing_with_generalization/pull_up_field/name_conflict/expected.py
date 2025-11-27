"""Example code for pull-up-field with name conflict."""


class Employee:
    def __init__(self, name):
        self.name = name  # Field already exists in parent


class Salesman(Employee):
    def __init__(self, name, sales_name):
        super().__init__(name)
        self.name = sales_name  # Trying to pull up this field would conflict


class Engineer(Employee):
    def __init__(self, name, eng_name):
        super().__init__(name)
        self.name = eng_name  # Trying to pull up this field would conflict
