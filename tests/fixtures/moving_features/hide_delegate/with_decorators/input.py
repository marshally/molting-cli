"""Example code for hide-delegate with decorators."""


class Employee:
    def __init__(self, compensation):
        self.compensation = compensation


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
