class JobItem:
    def __init__(self, quantity, unit_price):
        self.quantity = quantity
        self.unit_price = unit_price

    def get_unit_price(self):
        return self.unit_price

    def get_total_price(self):
        return self.get_unit_price() * self.quantity


class LaborItem(JobItem):
    def __init__(self, quantity, employee):
        super().__init__(quantity, 0)
        self.employee = employee

    def get_unit_price(self):
        return self.employee.rate
