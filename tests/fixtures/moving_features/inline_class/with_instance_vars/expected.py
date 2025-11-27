"""Example code for inline class with instance variables."""


class Employee:
    def __init__(self, name):
        self.name = name
        self.hours_worked = 0
        self.office_salary = 0
        self.office_bonus_percentage = 0
        self.office_deduction_rate = 0
        self.office_tax_rate = 0

    def calculate_gross_pay(self):
        """Calculate gross pay using compensation fields."""
        base_pay = self.office_salary
        bonus = self.office_salary * self.office_bonus_percentage
        return base_pay + bonus

    def calculate_net_pay(self):
        """Calculate net pay using compensation fields."""
        gross = self.office_salary + (self.office_salary * self.office_bonus_percentage)
        deductions = gross * self.office_deduction_rate
        taxes = gross * self.office_tax_rate
        return gross - deductions - taxes

    def get_annual_compensation(self):
        """Get annual compensation using compensation fields."""
        monthly_gross = self.office_salary + (
            self.office_salary * self.office_bonus_percentage
        )
        return monthly_gross * 12
