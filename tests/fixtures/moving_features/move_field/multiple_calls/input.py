"""Example code for move-field with multiple call sites."""


class Account:
    def __init__(self):
        self.balance = 1000
        self.interest_rate = 0.05

    def interest_for_days(self, days):
        return self.interest_rate * days

    def calculate_monthly_interest(self):
        return self.balance * self.interest_rate / 12

    def get_annual_interest(self):
        return self.balance * self.interest_rate


class AccountType:
    def __init__(self, name):
        self.name = name


class InterestCalculator:
    def __init__(self, account):
        self.account = account

    def project_earnings(self, years):
        principal = self.account.balance
        rate = self.account.interest_rate
        return principal * (1 + rate) ** years

    def compare_rates(self, other_account):
        return self.account.interest_rate - other_account.interest_rate
