def calculate_distance(scenario):
    temp = 2 * (scenario.primary_force / scenario.mass)
    primary_time = scenario.delay

    temp = scenario.secondary_force / scenario.mass
    secondary_time = scenario.delay + temp
