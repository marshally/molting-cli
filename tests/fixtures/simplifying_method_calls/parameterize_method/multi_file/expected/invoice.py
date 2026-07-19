from formatter import CurrencyFormatter


def generate_invoice(total, currency='USD'):
    formatter = CurrencyFormatter()
    if currency == 'USD':
        formatted = formatter.format_currency(total, "USD")
    else:
        formatted = formatter.format_currency(total, "EUR")
    return f"Invoice Total: {formatted}"


def quick_invoice(amount):
    formatter = CurrencyFormatter()
    return formatter.format_currency(amount, "USD")
