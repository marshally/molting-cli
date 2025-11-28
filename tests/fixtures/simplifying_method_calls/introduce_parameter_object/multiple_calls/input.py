"""Example code for introduce-parameter-object with multiple call sites."""


class Charge:
    def __init__(self, amount, date):
        self.amount = amount
        self.date = date


class Account:
    def __init__(self):
        self.charges = []

    def add_charge(self, amount, charge_date):
        self.charges.append(Charge(amount, charge_date))


def flow_between(start_date, end_date, account):
    return sum(charge.amount for charge in account.charges if start_date <= charge.date <= end_date)


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
