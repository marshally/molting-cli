"""Example code for move-method with decorators."""


class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self._balance = 0

    @property
    def balance(self):
        """Get the account balance with interest applied."""
        return self._balance + self.account_type.calculate_interest(self._balance)

    def deposit(self, amount):
        self._balance += amount


class AccountType:
    def __init__(self, interest_rate):
        self.interest_rate = interest_rate

    def calculate_interest(self, balance):
        return balance * self.interest_rate
