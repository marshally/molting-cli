"""Example code for replace-conditional-with-polymorphism with instance variables."""


class ShippingCalculator:
    def __init__(self, base_rate, weight_multiplier, distance_factor):
        self.base_rate = base_rate
        self.weight_multiplier = weight_multiplier
        self.distance_factor = distance_factor
        self.insurance_rate = 0.02

    def calculate_cost(self, weight, distance):
        raise NotImplementedError


class StandardShipping(ShippingCalculator):
    def calculate_cost(self, weight, distance):
        cost = self.base_rate + (weight * self.weight_multiplier)
        cost += distance * self.distance_factor * 0.5
        return cost


class ExpressShipping(ShippingCalculator):
    def calculate_cost(self, weight, distance):
        cost = self.base_rate * 1.5 + (weight * self.weight_multiplier * 1.2)
        cost += distance * self.distance_factor * 0.8
        return cost


class OvernightShipping(ShippingCalculator):
    def calculate_cost(self, weight, distance):
        cost = self.base_rate * 2.0 + (weight * self.weight_multiplier * 1.5)
        cost += distance * self.distance_factor * 1.2
        cost += cost * self.insurance_rate
        return cost
