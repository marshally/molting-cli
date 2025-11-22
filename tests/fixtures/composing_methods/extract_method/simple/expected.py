class Order:
    def __init__(self, name, orders):
        self.name = name
        self.orders = orders

    def print_owing(self):
        outstanding = 0
        self.print_banner()

        # calculate outstanding
        for order in self.orders:
            outstanding += order.amount

        # print details
        print(f"name: {self.name}")
        print(f"amount: {outstanding}")

    def print_banner(self):
        # print banner
        print("**************************")
        print("***** Customer Owes ******")
        print("**************************")
