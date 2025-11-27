class BankAccount:
    def __init__(self, account_number, balance):
        self.account_number = account_number
        self.balance = balance
        self.transaction_history = []
        self.overdraft_limit = 0

    def get_account_summary(self):
        summary = f"Account: {self.account_number}\n"
        summary += f"Balance: ${self.balance:.2f}\n"
        summary += f"Transactions: {len(self.transaction_history)}"
        return summary
