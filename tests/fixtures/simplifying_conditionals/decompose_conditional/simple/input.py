def calculate_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if date.month < 6 or date.month > 8:
        charge = quantity * winter_rate + winter_service_charge
    else:
        charge = quantity * summer_rate
    return charge
