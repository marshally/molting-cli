"""Example code for pull-up-method with decorators."""


class Employee:
    @staticmethod
    def format_currency(amount):
        return f"${amount:,.2f}"


class Salesman(Employee):
    pass


class Engineer(Employee):
    pass
