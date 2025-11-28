"""Example code for consolidate conditional expression with decorators."""


class EmployeeBenefits:
    def __init__(self, employee):
        self.employee = employee

    @property
    def disability_amount(self):
        if self.employee.seniority < 2:
            return 0
        if self.employee.months_disabled > 12:
            return 0
        if self.employee.is_part_time:
            return 0
        # calculate disability amount
        return 100
