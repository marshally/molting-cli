"""Expected output after pull-up-field with decorators."""


class Employee:
    @property
    def commission_rate(self):
        return self._commission_rate

    @commission_rate.setter
    def commission_rate(self, value):
        self._commission_rate = value


class Salesman(Employee):
    def __init__(self):
        self._commission_rate = 0.1


class Engineer(Employee):
    def __init__(self):
        self._commission_rate = 0.05
