"""Example code for preserve whole object with local variables."""


class Account:
    def __init__(self, balance, overdraft_limit):
        self.balance = balance
        self.overdraft_limit = overdraft_limit


class Transaction:
    def __init__(self, account):
        self.account = account

    def check_withdrawal(self, amount):
        """Check if withdrawal is allowed using local variables."""
        # Extract values into locals before passing
        current_balance = self.account.balance
        limit = self.account.overdraft_limit

        # Additional local processing
        available = current_balance + limit
        remaining_after = current_balance - amount

        # Pass individual values instead of whole object
        if can_withdraw(self.account, amount):
            print(f"Withdrawal allowed. Available: {available}, Remaining: {remaining_after}")
            return True
        else:
            print(f"Withdrawal denied. Available: {available}")
            return False


def can_withdraw(account, amount):
    """Check if withdrawal amount is within limits."""
    return account.balance + account.overdraft_limit >= amount
