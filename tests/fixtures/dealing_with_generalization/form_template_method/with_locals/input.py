"""Example code for form template method with local variables."""


class Site:
    pass


class ResidentialSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate
        self.TAX_RATE = 0.1

    def get_bill_amount(self):
        # Local variables for intermediate calculations
        base = self.units * self.rate
        adjusted_base = base * 1.0
        tax = adjusted_base * self.TAX_RATE
        final_amount = adjusted_base + tax
        return final_amount


class LifelineSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate
        self.TAX_RATE = 0.1

    def get_bill_amount(self):
        # Same pattern with local variables
        base = self.units * self.rate * 0.5
        adjusted_base = base * 1.0
        tax = adjusted_base * self.TAX_RATE * 0.2
        final_amount = adjusted_base + tax
        return final_amount
