"""Example code for self-encapsulate-field with instance variables."""


class Account:
    def __init__(self, balance, interest_rate):
        self.balance = balance
        self.interest_rate = interest_rate
        self.transaction_count = 0

    def deposit(self, amount):
        self.balance += amount
        self.transaction_count += 1

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.transaction_count += 1
            return True
        return False

    def apply_interest(self):
        interest = self.balance * self.interest_rate
        self.balance += interest
        self.transaction_count += 1

    def get_summary(self):
        return f"Balance: {self.balance}, Transactions: {self.transaction_count}"
