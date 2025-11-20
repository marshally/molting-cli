class Order:
    def __init__(self, name, orders):
        self.name = name
        self.orders = orders

    def print_owing(self):
        self.print_banner()
        outstanding = self.calculate_outstanding()
        self.print_details(outstanding)

    def print_banner(self):
        print("**************************")
        print("***** Customer Owes ******")
        print("**************************")

    def calculate_outstanding(self):
        outstanding = 0
        for order in self.orders:
            outstanding += order.amount
        return outstanding

    def print_details(self, outstanding):
        print(f"name: {self.name}")
        print(f"amount: {outstanding}")
