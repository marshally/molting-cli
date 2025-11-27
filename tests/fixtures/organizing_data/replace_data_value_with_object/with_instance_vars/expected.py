"""Expected output after replace-data-value-with-object with instance variables."""


class CustomerInfo:
    def __init__(self, name):
        self.name = name


class Invoice:
    def __init__(self, customer_name, customer_email):
        self.customer_name = CustomerInfo(customer_name)
        self.customer_email = customer_email
        self.items = []
        self.total = 0.0

    def add_item(self, item, price):
        self.items.append((item, price))
        self.total += price

    def send_invoice(self):
        print(f"Sending invoice to {self.customer_name.name} at {self.customer_email}")
        print(f"Total: ${self.total}")

    def get_customer_info(self):
        return f"{self.customer_name.name} ({self.customer_email})"
