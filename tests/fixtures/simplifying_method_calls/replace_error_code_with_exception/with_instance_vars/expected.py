class BankAccount:
    def __init__(self, balance, overdraft_limit):
        self.balance = balance
        self.overdraft_limit = overdraft_limit
        self.transaction_count = 0


def process_withdrawal(account, amount):
    max_withdrawal = account.balance + account.overdraft_limit
    if amount > max_withdrawal:
        raise ValueError("Amount exceeds balance")
    account.balance -= amount
    account.transaction_count += 1
