def calculate_distance(scenario):
    primary_acc = 2 * (scenario.primary_force / scenario.mass)
    primary_time = scenario.delay

    secondary_acc = scenario.secondary_force / scenario.mass
    secondary_time = scenario.delay + secondary_acc
