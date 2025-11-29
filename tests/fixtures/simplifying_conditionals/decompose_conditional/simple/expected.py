def calculate_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if is_winter(date):
        charge = winter_charge(quantity, winter_rate, winter_service_charge)
    else:
        charge = summer_charge(quantity, summer_rate)
    return charge


def is_winter(date):
    return date.month in (12, 1, 2)


def winter_charge(quantity, winter_rate, winter_service_charge):
    return quantity * winter_rate + winter_service_charge


def summer_charge(quantity, summer_rate):
    return quantity * summer_rate
