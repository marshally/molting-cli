"""Example code for move field with instance variables."""


class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.balance = 1000

    def calculate_interest(self):
        """Calculate interest using the interest_rate field."""
        return self.balance * self.account_type.interest_rate

    def apply_interest(self):
        """Apply interest using the interest_rate field."""
        interest = self.balance * self.account_type.interest_rate
        self.balance += interest
        return interest

    def get_annual_interest(self):
        """Get annual interest using the interest_rate field."""
        return self.balance * self.account_type.interest_rate * 12


class AccountType:
    def __init__(self, name):
        self.name = name
        self.interest_rate = 0.05
