"""Expected output after encapsulate-field with instance variables."""


class BankAccount:
    def __init__(self, owner, balance):
        self.owner = owner
        self._balance = balance
        self.interest_rate = 0.05

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        self._balance = value

    def calculate_interest(self):
        return self.balance * self.interest_rate

    def update_balance(self, amount):
        self.balance += amount
