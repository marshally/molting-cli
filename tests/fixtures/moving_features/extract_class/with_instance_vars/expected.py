"""Example code for extract class with instance variables."""


class Employee:
    def __init__(self, name, salary, bonus_percentage, deduction_rate, tax_rate):
        self.name = name
        self.hours_worked = 0
        self.office_compensation = Compensation(salary, bonus_percentage, deduction_rate, tax_rate)

    def calculate_gross_pay(self):
        return self.office_compensation.calculate_gross_pay()

    def calculate_net_pay(self):
        return self.office_compensation.calculate_net_pay()

    def get_annual_compensation(self):
        return self.office_compensation.get_annual_compensation()


class Compensation:
    def __init__(self, salary, bonus_percentage, deduction_rate, tax_rate):
        self.salary = salary
        self.bonus_percentage = bonus_percentage
        self.deduction_rate = deduction_rate
        self.tax_rate = tax_rate


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
