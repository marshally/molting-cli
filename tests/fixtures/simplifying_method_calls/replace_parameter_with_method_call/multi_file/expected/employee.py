"""Employee management system."""


class Employee:
    """Represents an employee with salary and bonus calculations."""

    def __init__(self, name, base_salary, performance_rating):
        self.name = name
        self.base_salary = base_salary
        self.performance_rating = performance_rating

    def get_salary(self):
        """Get the employee's base salary.

        Returns:
            Base salary amount
        """
        return self.base_salary

    def calculate_bonus(self):
        """Calculate bonus based on base salary and performance rating.

        Returns:
            Calculated bonus amount
        """
        base_salary = self.get_salary()
        if self.performance_rating >= 4.0:
            return base_salary * 0.20
        elif self.performance_rating >= 3.0:
            return base_salary * 0.10
        else:
            return base_salary * 0.05
