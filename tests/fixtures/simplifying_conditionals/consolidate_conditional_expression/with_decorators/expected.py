"""Example code for consolidate conditional expression with decorators."""


class EmployeeBenefits:
    def __init__(self, employee):
        self.employee = employee

    @property
    def disability_amount(self):
        if self.is_not_eligible_for_disability():
            return 0
        # calculate disability amount
        return 100

    def is_not_eligible_for_disability(self):
        return (
            self.employee.seniority < 2
            or self.employee.months_disabled > 12
            or self.employee.is_part_time
        )
