"""Example code for replace magic number with symbolic constant with local variables."""


def potential_energy(mass, height):
    return mass * 9.81 * height


def calculate_force(mass):
    # Using magic number in local variable computation
    gravity = 9.81
    force = mass * gravity
    return force


def terminal_velocity(mass, drag_coefficient):
    # Multiple local variables involving magic number
    g = 9.81
    numerator = 2 * mass * g
    denominator = drag_coefficient

    velocity_squared = numerator / denominator
    velocity = velocity_squared ** 0.5

    return velocity


def free_fall_distance(time):
    # Magic number used in complex expression with locals
    gravity = 9.81
    half_g = gravity / 2
    distance = half_g * (time ** 2)
    return distance
