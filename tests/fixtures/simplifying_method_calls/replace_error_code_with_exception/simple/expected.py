class Account:
    def __init__(self, balance):
        self.balance = balance


def withdraw(account, amount):
    if amount > account.balance:
        raise ValueError("Amount exceeds balance")
    account.balance -= amount
