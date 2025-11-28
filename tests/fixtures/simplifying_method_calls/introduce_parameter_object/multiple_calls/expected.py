"""Example code for introduce-parameter-object with multiple call sites."""


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


class Account:
    def __init__(self):
        self.charges = []

    def add_charge(self, amount, charge_date):
        self.charges.append(Charge(amount, charge_date))


def flow_between(date_range, account):
    return sum(charge.amount for charge in account.charges if date_range.includes(charge.date))


class FinancialReport:
    def calculate_period_total(self, account, start, end):
        return flow_between(start, end, account)

    def generate_summary(self, account, start, end):
        total = flow_between(start, end, account)
        return f"Total for period: ${total}"


def audit_account(account, period_start, period_end):
    total = flow_between(period_start, period_end, account)
    print(f"Audit: ${total}")
    return total


def compare_periods(account, start1, end1, start2, end2):
    period1 = flow_between(start1, end1, account)
    period2 = flow_between(start2, end2, account)
    return period1 - period2
