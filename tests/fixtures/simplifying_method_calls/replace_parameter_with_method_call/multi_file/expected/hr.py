"""Human Resources module."""

from employee import Employee


class HRManager:
    """Manages HR operations including compensation reviews."""

    def review_compensation(self, employee):
        """Review an employee's compensation and calculate potential bonus.

        Args:
            employee: Employee to review

        Returns:
            Dictionary with review details
        """
        salary = employee.get_salary()
        # Parameter removed - method calls get_salary() internally
        bonus = employee.calculate_bonus()

        return {
            "name": employee.name,
            "current_salary": salary,
            "proposed_bonus": bonus,
            "total_compensation": salary + bonus
        }

    def generate_compensation_report(self, employees):
        """Generate compensation report for multiple employees.

        Args:
            employees: List of employees to include in report

        Returns:
            List of compensation reviews
        """
        return [self.review_compensation(emp) for emp in employees]
