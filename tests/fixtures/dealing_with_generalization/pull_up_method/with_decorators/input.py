"""Example code for pull-up-method with decorators."""


class Employee:
    pass


class Salesman(Employee):
    @staticmethod
    def format_currency(amount):
        return f"${amount:,.2f}"


class Engineer(Employee):
    @staticmethod
    def format_currency(amount):
        return f"${amount:,.2f}"
