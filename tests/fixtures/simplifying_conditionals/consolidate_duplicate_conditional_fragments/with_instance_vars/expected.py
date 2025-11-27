"""Expected output after consolidate-duplicate-conditional-fragments with instance variables."""


class OrderProcessor:
    def __init__(self, special_discount, regular_discount):
        self.special_discount = special_discount
        self.regular_discount = regular_discount

    def process_order(self, is_special, price):
        if is_special:
            total = price * self.special_discount
        else:
            total = price * self.regular_discount
        self.send_order()
        return total

    def send_order(self):
        pass
