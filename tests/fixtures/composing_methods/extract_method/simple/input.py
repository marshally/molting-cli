"""Example code for simple extract method test."""


class Order:
    def __init__(self, name):
        self.name = name

    def print_owing(self):
        outstanding = 0

        # print banner
        print("**************************")
        print("***** Customer Owes ******")
        print("**************************")

        # calculate outstanding
        for order in self.orders:
            outstanding += order.amount

        # print details
        print(f"name: {self.name}")
        print(f"amount: {outstanding}")
