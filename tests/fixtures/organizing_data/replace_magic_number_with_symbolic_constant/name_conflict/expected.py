"""Example code for replace-magic-number-with-symbolic-constant with name conflict."""

GRAVITATIONAL_CONSTANT = 10.0  # Existing constant with the name we want to use


def potential_energy(mass, height):
    return mass * 9.81 * height
