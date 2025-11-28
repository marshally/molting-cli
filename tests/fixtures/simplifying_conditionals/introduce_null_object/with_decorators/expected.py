"""Expected output after introduce null object with decorators."""


class Site:
    def __init__(self, customer):
        self.customer = customer if customer is not None else NullCustomer()


class Customer:
    def __init__(self, name, plan="Premium", billing_history=None):
        self._name = name
        self._plan = plan
        self._billing_history = billing_history or []

    @property
    def name(self):
        return self._name

    @property
    def plan(self):
        return self._plan

    @property
    def billing_history(self):
        return self._billing_history

    def is_null(self):
        return False


class NullCustomer(Customer):
    def __init__(self):
        self._name = "Unknown"
        self._plan = "Basic"
        self._billing_history = []

    def is_null(self):
        return True


# Client code no longer needs null checks
