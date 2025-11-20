class HeatingPlan:
    def __init__(self, low, high):
        self.low = low
        self.high = high


class TempRange:
    def __init__(self, low, high):
        self.low = low
        self.high = high


def within_plan(plan, temp_range):
    return temp_range.low >= plan.low and temp_range.high <= plan.high
