class Calculator:
    def compute_discount(self, price, tax_rate, discount_factor):
        # Complex expression spanning multiple operations
        adjusted_price = price * (1 + tax_rate) * (1 - discount_factor)
        final_price = adjusted_price
        return final_price
