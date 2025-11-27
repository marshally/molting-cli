"""Example code for introduce parameter object with name conflict."""


class Charge:
    def __init__(self, amount, date):
        self.amount = amount
        self.date = date


class DateRange:
    """This class already exists - should conflict."""

    def __init__(self, start, end, timezone):
        self.start = start
        self.end = end
        self.timezone = timezone


class Account:
    def __init__(self):
        self.charges = []

    def add_charge(self, amount, charge_date):
        self.charges.append(Charge(amount, charge_date))


def flow_between(start_date, end_date, account):
    return sum(charge.amount for charge in account.charges if start_date <= charge.date <= end_date)
