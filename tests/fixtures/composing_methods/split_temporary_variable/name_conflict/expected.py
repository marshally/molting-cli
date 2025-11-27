"""Example code for split temporary variable with name conflict."""


def calculate_distance(scenario):
    primary_acc = 100  # This variable already exists - should cause conflict
    temp = 2 * (scenario.primary_force / scenario.mass)
    primary_time = scenario.delay

    temp = scenario.secondary_force / scenario.mass
    secondary_time = scenario.delay + temp
    return primary_acc
