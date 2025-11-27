"""Example code for introduce null object with decorators."""


class Site:
    def __init__(self, customer):
        self.customer = customer


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


# Client code would check: if customer is not None
