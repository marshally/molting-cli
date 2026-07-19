"""Employee class with type-based constructor."""


class Employee:
    """Employee with type code that could benefit from factory construction."""

    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, name, employee_type):
        self.name = name
        self.employee_type = employee_type

    def get_monthly_salary(self):
        """Calculate monthly salary based on employee type."""
        if self.employee_type == self.ENGINEER:
            return 5000
        elif self.employee_type == self.SALESMAN:
            return 4000
        elif self.employee_type == self.MANAGER:
            return 7000
        return 3000
