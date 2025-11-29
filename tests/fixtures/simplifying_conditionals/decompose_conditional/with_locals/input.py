def calculate_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    discount = 0.1
    tax_rate = 0.08

    if date.month < 6 or date.month > 8:
        base = quantity * winter_rate + winter_service_charge
        charge = base * (1 - discount) * (1 + tax_rate)
    else:
        base = quantity * summer_rate
        charge = base * (1 - discount) * (1 + tax_rate)

    return charge
