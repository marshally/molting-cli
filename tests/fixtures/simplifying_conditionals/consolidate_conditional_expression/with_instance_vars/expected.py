"""Expected output after consolidate-conditional-expression with instance variables."""


class BenefitsCalculator:
    def __init__(self, min_seniority, max_months_disabled):
        self.min_seniority = min_seniority
        self.max_months_disabled = max_months_disabled

    def disability_amount(self, employee):
        if self.is_not_eligible_for_disability(employee):
            return 0
        # calculate disability amount
        return 100

    def is_not_eligible_for_disability(self, employee):
        return (
            employee.seniority < self.min_seniority
            or employee.months_disabled > self.max_months_disabled
            or employee.is_part_time
        )
