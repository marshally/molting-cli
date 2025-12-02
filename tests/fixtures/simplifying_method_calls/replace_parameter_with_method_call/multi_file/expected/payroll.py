"""Payroll processing module."""

from employee import Employee


class PayrollProcessor:
    """Handles payroll calculations for employees."""

    def __init__(self):
        self.employees = []

    def add_employee(self, employee):
        """Add an employee to the payroll system."""
        self.employees.append(employee)

    def process_bonuses(self):
        """Process bonuses for all employees.

        Returns:
            Total bonus amount paid out
        """
        total_bonuses = 0
        for emp in self.employees:
            # Parameter removed - method calls get_salary() internally
            bonus = emp.calculate_bonus()
            total_bonuses += bonus
            print(f"{emp.name} receives bonus: ${bonus:.2f}")
        return total_bonuses
