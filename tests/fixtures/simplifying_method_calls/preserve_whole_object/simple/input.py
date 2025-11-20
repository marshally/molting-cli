class HeatingPlan:
    def __init__(self, low, high):
        self.low = low
        self.high = high


class TempRange:
    def __init__(self, low, high):
        self.low = low
        self.high = high


def within_plan(plan, low, high):
    return low >= plan.low and high <= plan.high
