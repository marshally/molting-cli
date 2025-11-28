"""Expected output after consolidate duplicate conditional fragments with decorators."""


class OrderProcessor:
    def __init__(self, price):
        self.price = price

    @property
    def total(self):
        if self.is_special:
            total = self.price * 0.95
        else:
            total = self.price * 0.98
        self.send_order()
        return total

    @property
    def is_special(self):
        return True

    def send_order(self):
        pass
