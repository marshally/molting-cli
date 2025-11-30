"""Example code for hide-delegate with decorators."""


class Employee:
    def __init__(self, compensation: "Compensation"):
        self._compensation = compensation
    def get_base_salary(self):
        return self._compensation.base_salary
    def get_bonus_rate(self):
        return self._compensation.bonus_rate
    @property
    def annual_bonus(self):
        return self._compensation.annual_bonus
    @property
    def total_compensation(self):
        return self._compensation.total_compensation


class Compensation:
    def __init__(self, base_salary):
        self.base_salary = base_salary
        self.bonus_rate = 0.1

    @property
    def annual_bonus(self):
        """Calculate annual bonus based on base salary."""
        return self.base_salary * self.bonus_rate

    @property
    def total_compensation(self):
        """Calculate total compensation including bonus."""
        return self.base_salary + self.annual_bonus
