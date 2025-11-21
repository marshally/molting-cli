def disability_amount(seniority, months_disabled, is_part_time):
    if seniority < 2 or months_disabled > 12 or is_part_time:
        return 0
    return calculate_disability()
