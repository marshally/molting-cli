"""Expected output after replace-error-code-with-exception with multiple call sites."""


class Account:
    def __init__(self, balance):
        self.balance = balance


def withdraw(account, amount):
    if amount > account.balance:
        raise ValueError("Amount exceeds balance")
    account.balance -= amount


class BankTeller:
    def process_withdrawal(self, account, amount):
        try:
            withdraw(account, amount)
            print(f"Withdrawal successful: ${amount}")
            return True
        except ValueError:
            print("Withdrawal failed: insufficient funds")
            return False

    def handle_transaction(self, account, amount):
        try:
            withdraw(account, amount)
            self.log_successful_transaction(amount)
        except ValueError:
            self.log_failed_transaction(amount)

    def log_failed_transaction(self, amount):
        print(f"Failed transaction: ${amount}")

    def log_successful_transaction(self, amount):
        print(f"Successful transaction: ${amount}")


def execute_withdrawal(account, amount):
    try:
        withdraw(account, amount)
        return "Success"
    except ValueError:
        return "Error: Insufficient balance"


def batch_withdraw(account, amounts):
    results = []
    for amount in amounts:
        try:
            withdraw(account, amount)
            results.append(f"Success: ${amount}")
        except ValueError:
            results.append(f"Failed: ${amount}")
    return results
