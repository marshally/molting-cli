class BankAccount:
    def __init__(self, account_number, balance):
        self.account_number = account_number
        self.balance = balance
        self.transaction_history = []
        self.overdraft_limit = 0

    def get_account_summary(self, include_overdraft=False):
        summary = f"Account: {self.account_number}\n"
        summary += f"Balance: ${self.balance:.2f}\n"
        summary += f"Transactions: {len(self.transaction_history)}"
        if include_overdraft:
            summary += f"\nOverdraft Limit: ${self.overdraft_limit:.2f}"
        return summary
