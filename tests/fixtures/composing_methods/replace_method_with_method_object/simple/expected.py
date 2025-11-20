class Account:
    def delta(self):
        return 5

    def gamma(self, input_val, quantity, year_to_date):
        return Gamma(self, input_val, quantity, year_to_date).compute()


class Gamma:
    def __init__(self, account, input_val, quantity, year_to_date):
        self.account = account
        self.input_val = input_val
        self.quantity = quantity
        self.year_to_date = year_to_date

    def compute(self):
        important_value1 = (self.input_val * self.quantity) + self.account.delta()
        important_value2 = (self.input_val * self.year_to_date) + 100
        important_thing = self._important_thing(important_value1, important_value2)
        return important_thing - 2 * important_value1

    def _important_thing(self, val1, val2):
        return val1 * val2
