"""Example code for move-method with multiple call sites."""


class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.balance = 1000
        self.days_overdrawn = 5

    def overdraft_charge(self):
        return self.account_type.overdraft_charge(self.days_overdrawn)

    def calculate_total_fees(self):
        overdraft = self.overdraft_charge()
        monthly_fee = 5.0
        return overdraft + monthly_fee

    def generate_statement(self):
        charge = self.overdraft_charge()
        return f"Balance: ${self.balance}, Overdraft charge: ${charge}"


class AccountType:
    def __init__(self, name, premium=False):
        self.name = name
        self.premium = premium

    def is_premium(self):
        return self.premium

    def overdraft_charge(self, days_overdrawn):
        if self.is_premium():
            result = 10
            if days_overdrawn > 7:
                result += (days_overdrawn - 7) * 0.85
            return result
        else:
            return days_overdrawn * 1.75


class Bank:
    def __init__(self):
        self.accounts = []

    def process_monthly_fees(self):
        total = 0
        for account in self.accounts:
            total += account.overdraft_charge()
        return total

    def report_overdraft_charges(self):
        charges = []
        for account in self.accounts:
            charge = account.overdraft_charge()
            if charge > 0:
                charges.append(charge)
        return charges
