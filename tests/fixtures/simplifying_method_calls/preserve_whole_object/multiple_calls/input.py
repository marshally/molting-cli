"""Example code for preserve-whole-object with multiple call sites."""


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


class TemperatureController:
    def __init__(self, plan):
        self.plan = plan

    def is_comfortable(self, temp_range):
        return within_plan(self.plan, temp_range.low, temp_range.high)

    def check_range(self, temp_range):
        if within_plan(self.plan, temp_range.low, temp_range.high):
            print("Temperature is within acceptable range")
        else:
            print("Temperature is outside acceptable range")


def validate_temperature(plan, temp_range):
    if within_plan(plan, temp_range.low, temp_range.high):
        return "Valid"
    return "Invalid"


def log_temperature_check(plan, temp_range):
    result = within_plan(plan, temp_range.low, temp_range.high)
    print(f"Temperature check: {result}")
    return result
