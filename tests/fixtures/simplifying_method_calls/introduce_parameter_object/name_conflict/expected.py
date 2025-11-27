"""Example code for introduce parameter object with name conflict."""


class Charge:
    def __init__(self, amount, date):
        self.amount = amount
        self.date = date


class DateRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def includes(self, date):
        return self.start <= date <= self.end


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


def flow_between(date_range, account):
    return sum(charge.amount for charge in account.charges if date_range.includes(charge.date))
