"""Expected output after replace-conditional-with-polymorphism with instance variables."""


class ShippingCalculator:
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"

    def __init__(self, shipping_type, base_rate, weight_multiplier, distance_factor):
        self.shipping_type = shipping_type
        self.base_rate = base_rate
        self.weight_multiplier = weight_multiplier
        self.distance_factor = distance_factor
        self.insurance_rate = 0.02

    def calculate_cost(self, weight, distance):
        if self.shipping_type == self.STANDARD:
            cost = self.base_rate + (weight * self.weight_multiplier)
            cost += distance * self.distance_factor * 0.5
        elif self.shipping_type == self.EXPRESS:
            cost = self.base_rate * 1.5 + (weight * self.weight_multiplier * 1.2)
            cost += distance * self.distance_factor * 0.8
        elif self.shipping_type == self.OVERNIGHT:
            cost = self.base_rate * 2.0 + (weight * self.weight_multiplier * 1.5)
            cost += distance * self.distance_factor * 1.2
            cost += cost * self.insurance_rate
        else:
            raise ValueError("Invalid shipping type")
        return cost
