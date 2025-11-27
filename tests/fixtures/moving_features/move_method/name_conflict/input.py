"""Example code for move-method with name conflict."""


class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.days_overdrawn = 0

    def overdraft_charge(self):
        """Method to be moved - but target class already has this method name."""
        if self.account_type.is_premium():
            result = 10
            if self.days_overdrawn > 7:
                result += (self.days_overdrawn - 7) * 0.85
            return result
        else:
            return self.days_overdrawn * 1.75


class AccountType:
    def is_premium(self):
        return True

    def overdraft_charge(self):
        """This method already exists - creating a name conflict."""
        return 5.0
