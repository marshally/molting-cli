class Order:
    def __init__(self, items):
        self.items = items
        self.tax_rate = 0.08

    def calculate_total(self, quantity, price):
        subtotal = quantity * price
        tax = subtotal * self.tax_rate
        return subtotal + tax

    def get_item_count(self):
        return len(self.items)
