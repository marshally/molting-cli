"""Example code for decompose-conditional with multiple call sites."""


def calculate_shipping_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if is_winter(date):
        charge = winter_charge(quantity, winter_rate, winter_service_charge)
    else:
        charge = summer_charge(quantity, summer_rate)
    return charge


def calculate_handling_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if is_winter(date):
        charge = winter_charge(quantity, winter_rate, winter_service_charge)
    else:
        charge = summer_charge(quantity, summer_rate)
    return charge * 0.1


def calculate_total_charge(quantity, date, winter_rate, summer_rate, winter_service_charge):
    if is_winter(date):
        base_charge = winter_charge(quantity, winter_rate, winter_service_charge)
    else:
        base_charge = summer_charge(quantity, summer_rate)

    tax = base_charge * 0.08
    return base_charge + tax


def is_winter(date):
    return date.month < 6 or date.month > 8


def winter_charge(quantity, winter_rate, winter_service_charge):
    return quantity * winter_rate + winter_service_charge


def summer_charge(quantity, summer_rate):
    return quantity * summer_rate
