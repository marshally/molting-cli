"""Example code for push-down-field with decorators."""


class Employee:
    pass


class Salesman(Employee):
    def __init__(self):
        self._sales_target = 10000

    @property
    def sales_target(self):
        return self._sales_target

    @sales_target.setter
    def sales_target(self, value):
        self._sales_target = value


class Engineer(Employee):
    pass
