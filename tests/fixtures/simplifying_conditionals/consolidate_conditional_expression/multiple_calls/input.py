"""Example code for consolidate-conditional-expression with multiple call sites."""


def disability_amount(employee):
    if employee.seniority < 2:
        return 0
    if employee.months_disabled > 12:
        return 0
    if employee.is_part_time:
        return 0
    # calculate disability amount
    return 100


def vacation_days(employee):
    if employee.seniority < 2:
        return 0
    if employee.months_disabled > 12:
        return 0
    if employee.is_part_time:
        return 0
    # calculate vacation days
    return employee.seniority * 2


def bonus_multiplier(employee):
    if employee.seniority < 2:
        return 0.5
    if employee.months_disabled > 12:
        return 0.5
    if employee.is_part_time:
        return 0.5
    # calculate bonus multiplier
    return 1.0 + (employee.seniority * 0.1)
