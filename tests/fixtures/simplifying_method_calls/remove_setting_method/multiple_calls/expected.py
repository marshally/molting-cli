"""Expected output after remove-setting-method with multiple call sites."""


class Account:
    def __init__(self, id):
        self._id = id

    def get_id(self):
        return self._id


class AccountManager:
    def __init__(self):
        self.accounts = []

    def create_account(self):
        account = Account(self.generate_id())
        self.accounts.append(account)
        return account

    def migrate_account(self, old_account):
        new_account = Account(old_account.get_id())
        return new_account

    def generate_id(self):
        return len(self.accounts) + 1


def initialize_account():
    account = Account(12345)
    return account


def clone_account(source):
    new_account = Account(source.get_id())
    return new_account
