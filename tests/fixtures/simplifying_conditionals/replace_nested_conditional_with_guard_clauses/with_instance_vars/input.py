"""Expected output after replace-nested-conditional-with-guard-clauses with instance variables."""


class PaymentCalculator:
    def __init__(self, part_time_rate, full_time_rate):
        self.part_time_rate = part_time_rate
        self.full_time_rate = full_time_rate

    def get_payment_amount(self, employee):
        if employee.is_separated:
            result = 0
        else:
            if employee.is_retired:
                result = 0
            else:
                if employee.is_part_time:
                    result = self.calculate_part_time_amount(employee)
                else:
                    result = self.calculate_full_time_amount(employee)
        return result

    def calculate_part_time_amount(self, employee):
        return employee.hours * self.part_time_rate

    def calculate_full_time_amount(self, employee):
        return employee.hours * self.full_time_rate
