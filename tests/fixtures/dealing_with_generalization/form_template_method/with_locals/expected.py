"""Expected output after form template method with local variables."""


class Site:
    TAX_RATE = 0.1

    def get_bill_amount(self):
        # Local variables for intermediate calculations
        base = self.get_base_amount()
        adjusted_base = self.adjust_base(base)
        tax = self.calculate_tax(adjusted_base)
        final_amount = adjusted_base + tax
        return final_amount

    def get_base_amount(self):
        raise NotImplementedError

    def adjust_base(self, base):
        raise NotImplementedError

    def calculate_tax(self, adjusted_base):
        raise NotImplementedError


class ResidentialSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate

    def get_base_amount(self):
        return self.units * self.rate

    def adjust_base(self, base):
        return base * 1.0

    def calculate_tax(self, adjusted_base):
        return adjusted_base * self.TAX_RATE


class LifelineSite(Site):
    def __init__(self, units, rate):
        self.units = units
        self.rate = rate

    def get_base_amount(self):
        return self.units * self.rate * 0.5

    def adjust_base(self, base):
        return base * 1.0

    def calculate_tax(self, adjusted_base):
        return adjusted_base * self.TAX_RATE * 0.2
