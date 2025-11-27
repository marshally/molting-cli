"""Example code for replace-exception-with-test with multiple call sites."""


def get_value_for_period(period_count, values):
    try:
        return values[period_count]
    except IndexError:
        return 0


class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process_period(self, period):
        value = get_value_for_period(period, self.data)
        return value * 2

    def get_average(self, periods):
        total = 0
        for period in periods:
            total += get_value_for_period(period, self.data)
        return total / len(periods) if periods else 0


def calculate_sum(values, periods):
    result = 0
    for period in periods:
        result += get_value_for_period(period, values)
    return result


def find_max_period(values):
    max_value = 0
    max_period = 0
    for i in range(100):
        value = get_value_for_period(i, values)
        if value > max_value:
            max_value = value
            max_period = i
    return max_period
