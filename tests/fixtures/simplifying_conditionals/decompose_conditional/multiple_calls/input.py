"""Expected output after decompose-conditional with multiple call sites."""


def calculate_shipping_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if date.month < 6 or date.month > 8:
        charge = quantity * winter_rate + winter_service_charge
    else:
        charge = quantity * summer_rate
    return charge


def calculate_handling_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if date.month < 6 or date.month > 8:
        charge = quantity * winter_rate + winter_service_charge
    else:
        charge = quantity * summer_rate
    return charge * 0.1


def calculate_total_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if date.month < 6 or date.month > 8:
        base_charge = quantity * winter_rate + winter_service_charge
    else:
        base_charge = quantity * summer_rate

    tax = base_charge * 0.08
    return base_charge + tax
