"""Expected output after move-field with multiple call sites."""


class Account:
    def __init__(self, account_type):
        self.balance = 1000
        self.account_type = account_type

    def interest_for_days(self, days):
        return self.account_type.interest_rate * days

    def calculate_monthly_interest(self):
        return self.balance * self.account_type.interest_rate / 12

    def get_annual_interest(self):
        return self.balance * self.account_type.interest_rate


class AccountType:
    def __init__(self, name):
        self.name = name
        self.interest_rate = 0.05


class InterestCalculator:
    def __init__(self, account):
        self.account = account

    def project_earnings(self, years):
        principal = self.account.balance
        rate = self.account.account_type.interest_rate
        return principal * (1 + rate) ** years

    def compare_rates(self, other_account):
        return self.account.account_type.interest_rate - other_account.account_type.interest_rate
