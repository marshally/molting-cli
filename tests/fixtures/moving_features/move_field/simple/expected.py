class Account:
    def __init__(self, account_type):
        self.account_type = account_type

    def interest_for_days(self, days):
        return self.account_type.interest_rate * days


class AccountType:
    def __init__(self):
        self.interest_rate = 0.05
