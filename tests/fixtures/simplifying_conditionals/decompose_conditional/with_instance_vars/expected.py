"""Example code for decompose-conditional with instance variables."""


class PricingCalculator:
    def __init__(self, winter_rate, summer_rate, winter_service_charge):
        self.winter_rate = winter_rate
        self.summer_rate = summer_rate
        self.winter_service_charge = winter_service_charge

    def calculate_charge(self, quantity, date):
        if self.is_winter(date):
            charge = self.winter_charge(quantity)
        else:
            charge = self.summer_charge(quantity)
        return charge

    def is_winter(self, date):
        return date.month in (12, 1, 2)

    def winter_charge(self, quantity):
        return quantity * self.winter_rate + self.winter_service_charge

    def summer_charge(self, quantity):
        return quantity * self.summer_rate
