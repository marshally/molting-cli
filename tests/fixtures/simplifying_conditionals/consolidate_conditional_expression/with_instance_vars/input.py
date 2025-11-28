"""Expected output after consolidate-conditional-expression with instance variables."""


class BenefitsCalculator:
    def __init__(self, min_seniority, max_months_disabled):
        self.min_seniority = min_seniority
        self.max_months_disabled = max_months_disabled

    def disability_amount(self, employee):
        if employee.seniority < self.min_seniority:
            return 0
        if employee.months_disabled > self.max_months_disabled:
            return 0
        if employee.is_part_time:
            return 0
        # calculate disability amount
        return 100
