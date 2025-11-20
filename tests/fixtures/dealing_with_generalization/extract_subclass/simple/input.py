class JobItem:
    def __init__(self, quantity, employee, is_labor, unit_price):
        self.quantity = quantity
        self.employee = employee
        self.is_labor = is_labor
        self.unit_price = unit_price

    def get_unit_price(self):
        if self.is_labor:
            return self.employee.rate
        return self.unit_price

    def get_total_price(self):
        return self.get_unit_price() * self.quantity
