"""Expected output after consolidate duplicate conditional fragments with local variables."""


def calculate_shipping(is_express, weight, distance):
    # Local variables used in duplicate code
    base_rate = 5.0
    fuel_surcharge = 1.25

    if is_express:
        cost = weight * 2.0
        total = cost + base_rate + fuel_surcharge
    else:
        cost = weight * 1.0
        total = cost + base_rate + fuel_surcharge

    log_shipment("express" if is_express else "standard", total)
    return total


def log_shipment(type, total):
    pass
