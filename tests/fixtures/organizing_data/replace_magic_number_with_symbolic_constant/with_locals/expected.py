"""Expected output after replace magic number with symbolic constant with local variables."""


GRAVITATIONAL_CONSTANT = 9.81


def potential_energy(mass, height):
    return mass * GRAVITATIONAL_CONSTANT * height


def calculate_force(mass):
    # Using magic number in local variable computation
    gravity = GRAVITATIONAL_CONSTANT
    force = mass * gravity
    return force


def terminal_velocity(mass, drag_coefficient):
    # Multiple local variables involving magic number
    g = GRAVITATIONAL_CONSTANT
    numerator = 2 * mass * g
    denominator = drag_coefficient

    velocity_squared = numerator / denominator
    velocity = velocity_squared ** 0.5

    return velocity


def free_fall_distance(time):
    # Magic number used in complex expression with locals
    gravity = GRAVITATIONAL_CONSTANT
    half_g = gravity / 2
    distance = half_g * (time ** 2)
    return distance
