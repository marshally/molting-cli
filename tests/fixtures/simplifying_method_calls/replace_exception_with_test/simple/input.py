def get_value_for_period(period_count, values):
    try:
        return values[period_count]
    except IndexError:
        return 0
