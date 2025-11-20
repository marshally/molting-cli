def get_payment_amount(employee):
    if employee.is_separated:
        return 0
    if employee.is_retired:
        return 0
    if employee.is_part_time:
        return calculate_part_time_amount(employee)
    return calculate_full_time_amount(employee)


def calculate_part_time_amount(employee):
    return 50


def calculate_full_time_amount(employee):
    return 100
