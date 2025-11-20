def discount(input_val, quantity, year_to_date):
    if input_val > 50:
        input_val -= 2
    if quantity > 100:
        input_val -= 1
    if year_to_date > 10000:
        input_val -= 4
    return input_val
