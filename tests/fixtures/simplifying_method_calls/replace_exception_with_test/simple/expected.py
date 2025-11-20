def get_value_for_period(period_count, values):
    if period_count >= len(values):
        return 0
    return values[period_count]
