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
        if self.date.month in (12, 1, 2):
            charge = self.quantity * self.winter_rate + self.winter_service_charge
        else:
            charge = self.quantity * self.summer_rate
        return charge
