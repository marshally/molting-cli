class Account:
    def __init__(self):
        self.interest_rate = 0.05

    def interest_for_days(self, days):
        return self.interest_rate * days


class AccountType:
    pass
