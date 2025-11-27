"""Example code for rename method with name conflict."""


class Customer:
    def __init__(self):
        self.invoice_credit_limit = 1000

    def get_inv_cdtlmt(self):
        return self.invoice_credit_limit

    def get_invoice_credit_limit(self):
        """This method already exists - should conflict."""
        return self.invoice_credit_limit * 1.1
