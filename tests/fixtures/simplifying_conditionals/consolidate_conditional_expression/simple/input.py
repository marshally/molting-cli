def disability_amount(seniority, months_disabled, is_part_time):
    if seniority < 2:
        return 0
    if months_disabled > 12:
        return 0
    if is_part_time:
        return 0
    return calculate_disability()
