class CurrencyFormatter:
    def __init__(self, locale="en_US"):
        self.locale = locale

    def format_currency(self, amount, currency="USD"):
        if currency == "USD":
            return f"${amount:.2f}"
        elif currency == "EUR":
            return f"€{amount:.2f}"
        else:
            return f"{currency} {amount:.2f}"

    def get_locale(self):
        return self.locale
