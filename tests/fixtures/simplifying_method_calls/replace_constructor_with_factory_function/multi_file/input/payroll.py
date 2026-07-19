"""Payroll module that processes employee salaries."""

from employee import Employee


class PayrollProcessor:
    """Process payroll for employees."""

    def __init__(self):
        self.processed = []

    def process_salary(self, name, emp_type):
        """Process salary for a new employee."""
        employee = Employee(name, emp_type)
        salary = employee.get_monthly_salary()
        self.processed.append((employee, salary))
        return salary

    def process_bonus(self, name, emp_type, bonus_multiplier):
        """Process bonus for an employee."""
        emp = Employee(name, emp_type)
        base_salary = emp.get_monthly_salary()
        return base_salary * bonus_multiplier
