class Account:
    def __init__(self, balance):
        self.balance = balance


def withdraw(account, amount):
    if amount > account.balance:
        return -1  # Error code
    else:
        account.balance -= amount
        return 0  # Success
