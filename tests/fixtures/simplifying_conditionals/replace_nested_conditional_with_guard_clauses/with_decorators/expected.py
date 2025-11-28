"""Expected output after replace nested conditional with guard clauses with decorators."""


class PaymentCalculator:
    def __init__(self, employee):
        self.employee = employee

    @property
    def payment_amount(self):
        if self.employee.is_separated:
            return 0
        if self.employee.is_retired:
            return 0
        if self.employee.is_part_time:
            return self.calculate_part_time_amount()
        return self.calculate_full_time_amount()

    def calculate_part_time_amount(self):
        return 50

    def calculate_full_time_amount(self):
        return 100
