def calculate_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if date.month in (12, 1, 2):
        charge = quantity * winter_rate + winter_service_charge
    else:
        charge = quantity * summer_rate
    return charge
