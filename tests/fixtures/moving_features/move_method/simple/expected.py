class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.days_overdrawn = 0

    def overdraft_charge(self):
        return self.account_type.overdraft_charge(self.days_overdrawn)


class AccountType:
    def is_premium(self):
        return True

    def overdraft_charge(self, days_overdrawn):
        if self.is_premium():
            result = 10
            if days_overdrawn > 7:
                result += (days_overdrawn - 7) * 0.85
            return result
        else:
            return days_overdrawn * 1.75
