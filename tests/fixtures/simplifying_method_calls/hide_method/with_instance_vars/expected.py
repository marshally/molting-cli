class PriceCalculator:
    def __init__(self, base_price, tax_rate, discount_rate):
        self.base_price = base_price
        self.tax_rate = tax_rate
        self.discount_rate = discount_rate
        self.currency = "USD"

    def calculate_final_price(self):
        discounted = self._apply_discount()
        return discounted + (discounted * self.calculate_tax())

    def _apply_discount(self):
        return self.base_price * (1 - self.discount_rate)

    def calculate_tax(self):
        return self.tax_rate
