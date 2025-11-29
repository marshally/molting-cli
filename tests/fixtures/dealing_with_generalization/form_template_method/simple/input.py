class Site:
    pass


class ResidentialSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate

    def get_bill_amount(self):
        base = self.units * self.rate
        tax = base * 0.1
        return base + tax


class LifelineSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate

    def get_bill_amount(self):
        base = self.units * self.rate * 0.5
        tax = base * 0.02
        return base + tax
