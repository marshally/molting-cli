"""Example code for push-down-field with name conflict."""


class Employee:
    def __init__(self):
        self.quota = 0  # Field to be pushed down


class Salesman(Employee):
    def __init__(self):
        super().__init__()
        self.quota = 1000  # Field already exists in target subclass


class Engineer(Employee):
    def __init__(self):
        super().__init__()
