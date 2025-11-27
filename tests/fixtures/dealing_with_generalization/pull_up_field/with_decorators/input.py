"""Example code for pull-up-field with decorators."""


class Employee:
    pass


class Salesman(Employee):
    def __init__(self):
        self._commission_rate = 0.1

    @property
    def commission_rate(self):
        return self._commission_rate

    @commission_rate.setter
    def commission_rate(self, value):
        self._commission_rate = value


class Engineer(Employee):
    def __init__(self):
        self._commission_rate = 0.05

    @property
    def commission_rate(self):
        return self._commission_rate

    @commission_rate.setter
    def commission_rate(self, value):
        self._commission_rate = value
