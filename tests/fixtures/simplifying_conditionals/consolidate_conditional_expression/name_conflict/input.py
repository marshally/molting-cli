"""Expected output after consolidate-conditional-expression with name conflict."""


def is_not_eligible_for_disability(employee):
    """Existing function with the target name."""
    return employee.age > 65


def disability_amount(employee):
    if employee.seniority < 2:
        return 0
    if employee.months_disabled > 12:
        return 0
    if employee.is_part_time:
        return 0
    # calculate disability amount
    return 100
