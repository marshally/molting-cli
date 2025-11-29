class Site:
    def get_bill_amount(self):
        base = self.get_base_amount()
        tax = self.get_tax_amount(base)
        return base + tax

    def get_base_amount(self):
        raise NotImplementedError

    def get_tax_amount(self, base):
        raise NotImplementedError


class ResidentialSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate

    def get_base_amount(self):
        return self.units * self.rate

    def get_tax_amount(self, base):
        return base * 0.1


class LifelineSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate

    def get_base_amount(self):
        return self.units * self.rate * 0.5

    def get_tax_amount(self, base):
        return base * 0.02
