"""Example code for replace-data-value-with-object with name conflict."""


class Customer:
    """Existing class with the name we want to use."""

    def __init__(self, name):
        self.name = name


class Order:
    def __init__(self, customer_name):
        self.customer = customer_name

    def get_customer_name(self):
        return self.customer
