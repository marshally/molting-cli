class Order:
    def __init__(self, customer_name):
        self.customer = Customer.get_named(customer_name)


class Customer:
    _instances = {}

    def __init__(self, name):
        self.name = name

    @classmethod
    def get_named(cls, name):
        if name not in cls._instances:
            cls._instances[name] = Customer(name)
        return cls._instances[name]
