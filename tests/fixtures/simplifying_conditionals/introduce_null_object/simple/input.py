class Site:
    def __init__(self, customer):
        self.customer = customer


class Customer:
    def __init__(self, name, plan="Premium"):
        self.name = name
        self.plan = plan


# Client code would check: if customer is not None
