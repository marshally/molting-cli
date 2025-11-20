class Order:
    def __init__(self, customer_name):
        self.customer = Customer(customer_name)


class Customer:
    def __init__(self, name):
        self.name = name
