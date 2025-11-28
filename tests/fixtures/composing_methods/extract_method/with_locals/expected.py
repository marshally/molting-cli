"""Expected output after extract method with local variables."""


class Order:
    def __init__(self, name, orders):
        self.name = name
        self.orders = orders

    def print_owing(self):
        outstanding = 0

        # print banner
        print("**************************")
        print("***** Customer Owes ******")
        print("**************************")

        outstanding = self.calculate_outstanding()

        # print details
        print(f"name: {self.name}")
        print(f"amount: {outstanding}")

    def calculate_outstanding(self):
        outstanding = 0
        for order in self.orders:
            outstanding += order.amount
        return outstanding
