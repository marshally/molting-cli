"""Example code for hide delegate with instance variables."""


class Employee:
    def __init__(self, compensation):
        self.compensation = compensation
        self.name = ""
        self.hours_worked = 0


class Compensation:
    def __init__(self):
        self.salary = 0
        self.bonus_percentage = 0
        self.deduction_rate = 0
        self.tax_rate = 0

    def calculate_gross_pay(self):
        """Calculate gross pay using compensation fields."""
        base_pay = self.salary
        bonus = self.salary * self.bonus_percentage
        return base_pay + bonus

    def calculate_net_pay(self):
        """Calculate net pay using compensation fields."""
        gross = self.salary + (self.salary * self.bonus_percentage)
        deductions = gross * self.deduction_rate
        taxes = gross * self.tax_rate
        return gross - deductions - taxes

    def get_annual_compensation(self):
        """Get annual compensation using compensation fields."""
        monthly_gross = self.salary + (self.salary * self.bonus_percentage)
        return monthly_gross * 12
