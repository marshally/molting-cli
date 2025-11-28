"""Example code for replace-data-value-with-object with multiple call sites."""


class Order:
    def __init__(self, customer_name):
        self.customer = customer_name

    def get_customer_name(self):
        return self.customer

    def print_details(self):
        print(f"Order for: {self.customer}")


class OrderProcessor:
    def __init__(self):
        self.orders = []

    def add_order(self, customer_name):
        order = Order(customer_name)
        self.orders.append(order)

    def process_orders(self):
        for order in self.orders:
            # Multiple accesses to customer field
            print(f"Processing order for {order.customer}")
            if order.customer.startswith("VIP"):
                print(f"Priority shipping for {order.customer}")


def create_order_report(order):
    # Another access to customer field
    return f"Customer: {order.customer}"
