"""Example code for encapsulate-field with instance variables."""


class BankAccount:
    def __init__(self, owner, balance):
        self.owner = owner
        self.balance = balance
        self.interest_rate = 0.05

    def calculate_interest(self):
        return self.balance * self.interest_rate

    def update_balance(self, amount):
        self.balance += amount
