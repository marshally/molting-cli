class Order:
    def calculate_total(self, is_premium):
        if is_premium:
            total = self.price * 0.9
            self.log_discount()
        else:
            total = self.price * 1.0
            self.log_discount()
        return total

    def log_discount(self):
        pass
