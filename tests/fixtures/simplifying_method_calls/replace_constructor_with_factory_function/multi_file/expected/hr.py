"""HR module that creates and manages employees."""

from employee import Employee, create_employee


class HRDepartment:
    """HR department managing employee records."""

    def __init__(self):
        self.employees = []

    def hire_manager(self, name):
        """Hire a new manager."""
        manager = create_employee(name, Employee.MANAGER)
        self.employees.append(manager)
        return manager

    def hire_engineer(self, name):
        """Hire a new engineer."""
        engineer = create_employee(name, Employee.ENGINEER)
        self.employees.append(engineer)
        return engineer

    def get_total_payroll(self):
        """Calculate total monthly payroll."""
        return sum(emp.get_monthly_salary() for emp in self.employees)
