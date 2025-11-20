class Calculator:
    def compute_discount(self, price, tax_rate, discount_factor):
        # Complex expression spanning multiple operations
        final_price = price * (1 + tax_rate) * (1 - discount_factor)
        return final_price
