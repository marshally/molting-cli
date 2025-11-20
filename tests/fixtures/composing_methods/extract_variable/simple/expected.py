def calculate_total(price, tax_rate):
    tax_amount = 1 + tax_rate
    total = price * tax_amount
    return total
