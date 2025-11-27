"""Example code for move method with local variables."""


class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.days_overdrawn = 0
        self.balance = 1000

    def calculate_fees(self):
        """Calculate fees with local variable accumulation."""
        total_fees = 0

        # Base overdraft charge
        if self.days_overdrawn > 0:
            overdraft = self.days_overdrawn * 1.75
            if self.account_type.is_premium():
                overdraft = overdraft * 0.5
            total_fees += overdraft

        # Monthly maintenance fee
        monthly_fee = 10
        if self.account_type.is_premium():
            monthly_fee = 5
        total_fees += monthly_fee

        return total_fees


class AccountType:
    def __init__(self, name):
        self.name = name

    def is_premium(self):
        return self.name == "Premium"
