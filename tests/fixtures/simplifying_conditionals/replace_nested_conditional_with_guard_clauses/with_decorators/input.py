"""Example code for replace nested conditional with guard clauses with decorators."""


class PaymentCalculator:
    def __init__(self, employee):
        self.employee = employee

    @property
    def payment_amount(self):
        if self.employee.is_separated:
            result = 0
        else:
            if self.employee.is_retired:
                result = 0
            else:
                if self.employee.is_part_time:
                    result = self.calculate_part_time_amount()
                else:
                    result = self.calculate_full_time_amount()
        return result

    def calculate_part_time_amount(self):
        return 50

    def calculate_full_time_amount(self):
        return 100
