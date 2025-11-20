class Order:
    def __init__(self, customer):
        self._customer = None
        self.set_customer(customer)

    def set_customer(self, customer):
        if self._customer is not None:
            self._customer.remove_order(self)
        self._customer = customer
        if customer is not None:
            customer.add_order(self)


class Customer:
    def __init__(self):
        self._orders = set()

    def add_order(self, order):
        self._orders.add(order)

    def remove_order(self, order):
        self._orders.discard(order)
