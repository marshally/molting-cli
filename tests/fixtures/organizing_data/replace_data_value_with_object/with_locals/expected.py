"""Example code for replace data value with object with local variables."""


class Customer:
    def __init__(self, name):
        self.name = name


class Order:
    def __init__(self, customer_name):
        self.customer = Customer(customer_name)

    def get_customer_name(self):
        return self.customer.name

    def print_customer_info(self):
        # Using customer in local variable computations
        name = self.customer.name
        upper_name = name.upper()
        formatted = f"Customer: {upper_name}"
        print(formatted)

    def validate_customer(self):
        # Local variable that processes the customer value
        customer_name = self.customer.name
        is_valid = len(customer_name) > 0 and customer_name.isalpha()
        return is_valid
