"""Example code for replace-error-code-with-exception with multiple call sites."""


class Account:
    def __init__(self, balance):
        self.balance = balance


def withdraw(account, amount):
    if amount > account.balance:
        raise ValueError("Amount exceeds balance")
    account.balance -= amount


class BankTeller:
    def process_withdrawal(self, account, amount):
        result = withdraw(account, amount)
        if result == -1:
            print("Withdrawal failed: insufficient funds")
            return False
        print(f"Withdrawal successful: ${amount}")
        return True

    def handle_transaction(self, account, amount):
        status = withdraw(account, amount)
        if status == -1:
            self.log_failed_transaction(amount)
        else:
            self.log_successful_transaction(amount)

    def log_failed_transaction(self, amount):
        print(f"Failed transaction: ${amount}")

    def log_successful_transaction(self, amount):
        print(f"Successful transaction: ${amount}")


def execute_withdrawal(account, amount):
    code = withdraw(account, amount)
    if code == -1:
        return "Error: Insufficient balance"
    return "Success"


def batch_withdraw(account, amounts):
    results = []
    for amount in amounts:
        code = withdraw(account, amount)
        if code == -1:
            results.append(f"Failed: ${amount}")
        else:
            results.append(f"Success: ${amount}")
    return results
