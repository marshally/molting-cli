"""Expected output after change-reference-to-value with instance variables."""


class Money:
    def __init__(self, amount, currency_code):
        self.amount = amount
        self.currency_code = currency_code

    def __eq__(self, other):
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount

    def __hash__(self):
        return hash(self.amount)
