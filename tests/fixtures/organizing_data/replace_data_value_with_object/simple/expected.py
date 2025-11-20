class Customer:
    def __init__(self, name):
        self.name = name


class Order:
    def __init__(self, customer_name):
        self.customer = Customer(customer_name)

    def get_customer_name(self):
        return self.customer.name
