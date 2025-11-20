class Site:
    def __init__(self, customer):
        self.customer = customer if customer is not None else NullCustomer()


class Customer:
    def __init__(self, name, plan="Premium"):
        self.name = name
        self.plan = plan

    def is_null(self):
        return False


class NullCustomer(Customer):
    def __init__(self):
        self.name = "Unknown"
        self.plan = "Basic"

    def is_null(self):
        return True


# Client code no longer needs null checks
