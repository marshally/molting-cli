"""Example code for change-reference-to-value with instance variables."""


class Money:
    _instances = {}

    def __init__(self, amount, currency_code):
        self.amount = amount
        self.currency_code = currency_code

    @classmethod
    def get(cls, amount, currency_code):
        key = (amount, currency_code)
        if key not in cls._instances:
            cls._instances[key] = Money(amount, currency_code)
        return cls._instances[key]
