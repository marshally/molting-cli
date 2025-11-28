"""Example code for replace-data-value-with-object with multiple call sites."""


class Customer:
    def __init__(self, name):
        self.name = name


class Order:
    def __init__(self, customer_name):
        self.customer = Customer(customer_name)

    def get_customer_name(self):
        return self.customer.name

    def print_details(self):
        print(f"Order for: {self.customer.name}")


class OrderProcessor:
    def __init__(self):
        self.orders = []

    def add_order(self, customer_name):
        order = Order(customer_name)
        self.orders.append(order)

    def process_orders(self):
        for order in self.orders:
            # Multiple accesses to customer field
            print(f"Processing order for {order.customer.name}")
            if order.customer.name.startswith("VIP"):
                print(f"Priority shipping for {order.customer.name}")


def create_order_report(order):
    # Another access to customer field
    return f"Customer: {order.customer.name}"
