"""Example code for preserve whole object with local variables."""


class Account:
    def __init__(self, balance, overdraft_limit):
        self.balance = balance
        self.overdraft_limit = overdraft_limit


class Transaction:
    def __init__(self, account):
        self.account = account

    def check_withdrawal(self, amount):
        """Check if withdrawal is allowed using the whole account object."""
        # Local processing still uses the original object
        current_balance = self.account.balance
        limit = self.account.overdraft_limit
        available = current_balance + limit
        remaining_after = current_balance - amount

        # Pass whole object instead of individual values
        if can_withdraw(self.account, amount):
            print(f"Withdrawal allowed. Available: {available}, Remaining: {remaining_after}")
            return True
        else:
            print(f"Withdrawal denied. Available: {available}")
            return False


def can_withdraw(account, amount):
    """Check if withdrawal amount is within limits."""
    return account.balance + account.overdraft_limit >= amount
