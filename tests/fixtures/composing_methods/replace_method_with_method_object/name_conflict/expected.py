"""Example code for replace method with method object with name conflict."""


class Gamma:
    """This class already exists - should cause conflict."""

    def existing_method(self):
        return "Existing Gamma class"


class Account:
    def delta(self):
        return 5

    def gamma(self, input_val, quantity, year_to_date):
        important_value1 = (input_val * quantity) + self.delta()
        important_value2 = (input_val * year_to_date) + 100
        important_thing = self._important_thing(important_value1, important_value2)
        return important_thing - 2 * important_value1

    def _important_thing(self, val1, val2):
        return val1 * val2
