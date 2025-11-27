"""Example code for move-field with name conflict."""


class Account:
    def __init__(self):
        self.interest_rate = 0.05

    def interest_for_days(self, days):
        return self.interest_rate * days


class AccountType:
    def __init__(self):
        self.interest_rate = 0.03  # Field already exists - creating name conflict
