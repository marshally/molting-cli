def calculate_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    discount = 0.1
    tax_rate = 0.08

    if is_winter(date):
        base = quantity * winter_rate + winter_service_charge
        charge = winter_charge(base, discount, tax_rate)
    else:
        base = quantity * summer_rate
        charge = summer_charge(base, tax_rate)

    return charge


def is_winter(date):
    return date.month in (12, 1, 2)


def winter_charge(base, discount, tax_rate):
    return base * (1 - discount) * (1 + tax_rate)


def summer_charge(base, tax_rate):
    return base * (1 + tax_rate)
