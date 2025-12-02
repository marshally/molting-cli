class CurrencyFormatter:
    def __init__(self, locale="en_US"):
        self.locale = locale

    def format_dollars(self, amount):
        return f"${amount:.2f}"

    def format_euros(self, amount):
        return f"€{amount:.2f}"

    def get_locale(self):
        return self.locale
