"""Expected output after decompose-conditional with instance variables."""


class PricingCalculator:
    def __init__(self, winter_rate, summer_rate, winter_service_charge):
        self.winter_rate = winter_rate
        self.summer_rate = summer_rate
        self.winter_service_charge = winter_service_charge

    def calculate_charge(self, quantity, date):
        if date.month < 6 or date.month > 8:
            charge = quantity * self.winter_rate + self.winter_service_charge
        else:
            charge = quantity * self.summer_rate
        return charge
