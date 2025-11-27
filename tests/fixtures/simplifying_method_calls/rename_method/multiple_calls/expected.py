"""Expected output after rename-method with multiple call sites."""


class Customer:
    def __init__(self):
        self.invoice_credit_limit = 1000

    def get_invoice_credit_limit(self):
        return self.invoice_credit_limit

    def display_credit_info(self):
        limit = self.get_invoice_credit_limit()
        print(f"Credit limit: {limit}")

    def check_purchase_allowed(self, amount):
        if amount > self.get_invoice_credit_limit():
            return False
        return True


class OrderProcessor:
    def __init__(self, customer):
        self.customer = customer

    def process_order(self, order_total):
        credit = self.customer.get_invoice_credit_limit()
        if order_total <= credit:
            print("Order approved")
        else:
            print("Order rejected - insufficient credit")

    def generate_report(self):
        customer_limit = self.customer.get_invoice_credit_limit()
        return f"Customer credit limit: {customer_limit}"


def check_customer_status(customer):
    limit = customer.get_invoice_credit_limit()
    if limit > 500:
        return "Premium customer"
    return "Standard customer"
