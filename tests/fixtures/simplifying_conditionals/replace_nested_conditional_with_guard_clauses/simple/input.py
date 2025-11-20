def get_payment_amount(employee):
    if employee.is_separated:
        result = 0
    else:
        if employee.is_retired:
            result = 0
        else:
            if employee.is_part_time:
                result = calculate_part_time_amount(employee)
            else:
                result = calculate_full_time_amount(employee)
    return result


def calculate_part_time_amount(employee):
    return 50


def calculate_full_time_amount(employee):
    return 100
