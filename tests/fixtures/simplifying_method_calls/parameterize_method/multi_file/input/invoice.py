from formatter import CurrencyFormatter


def generate_invoice(total, currency='USD'):
    formatter = CurrencyFormatter()
    if currency == 'USD':
        formatted = formatter.format_dollars(total)
    else:
        formatted = formatter.format_euros(total)
    return f"Invoice Total: {formatted}"


def quick_invoice(amount):
    formatter = CurrencyFormatter()
    return formatter.format_dollars(amount)
