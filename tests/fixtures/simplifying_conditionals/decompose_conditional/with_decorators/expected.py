"""Example code for decompose conditional with decorators."""


class PriceCalculator:
    def __init__(self, date, quantity, winter_rate, summer_rate, winter_service_charge):
        self.date = date
        self.quantity = quantity
        self.winter_rate = winter_rate
        self.summer_rate = summer_rate
        self.winter_service_charge = winter_service_charge

    @property
    def charge(self):
        if self.is_winter():
            charge = self.winter_charge()
        else:
            charge = self.summer_charge()
        return charge

    def is_winter(self):
        return self.date.month in (12, 1, 2)

    def winter_charge(self):
        return self.quantity * self.winter_rate + self.winter_service_charge

    def summer_charge(self):
        return self.quantity * self.summer_rate
