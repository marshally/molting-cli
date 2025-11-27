"""Example code for move method with instance variables."""


class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.balance = 1000
        self.days_overdrawn = 0
        self.overdraft_limit = 500

    def calculate_interest(self):
        """Calculate interest heavily using instance variables."""
        base_rate = self.account_type.base_interest_rate

        # Adjust for balance
        if self.balance > 10000:
            balance_bonus = base_rate * 0.5
        else:
            balance_bonus = 0

        # Penalty for overdraft
        if self.days_overdrawn > 0:
            overdraft_penalty = base_rate * 0.2 * self.days_overdrawn
        else:
            overdraft_penalty = 0

        # Calculate final interest
        total_rate = base_rate + balance_bonus - overdraft_penalty
        interest = self.balance * total_rate

        return interest


class AccountType:
    def __init__(self, name, base_interest_rate):
        self.name = name
        self.base_interest_rate = base_interest_rate
