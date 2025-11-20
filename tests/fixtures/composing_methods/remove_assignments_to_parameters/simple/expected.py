def discount(input_val, quantity, year_to_date):
    result = input_val
    if result > 50:
        result -= 2
    if quantity > 100:
        result -= 1
    if year_to_date > 10000:
        result -= 4
    return result
