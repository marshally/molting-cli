from formatter import CurrencyFormatter


def format_account_statement(balance):
    formatter = CurrencyFormatter()
    formatted_balance = formatter.format_dollars(balance)
    return f"Current Balance: {formatted_balance}"


def format_transaction(amount, transaction_type):
    formatter = CurrencyFormatter()
    formatted = formatter.format_dollars(amount)
    return f"{transaction_type}: {formatted}"
