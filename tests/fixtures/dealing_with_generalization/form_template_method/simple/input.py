class Site:
    pass


class ResidentialSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate
        self.TAX_RATE = 0.1

    def get_bill_amount(self):
        base = self.units * self.rate
        tax = base * self.TAX_RATE
        return base + tax


class LifelineSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate
        self.TAX_RATE = 0.1

    def get_bill_amount(self):
        base = self.units * self.rate * 0.5
        tax = base * self.TAX_RATE * 0.2
        return base + tax
