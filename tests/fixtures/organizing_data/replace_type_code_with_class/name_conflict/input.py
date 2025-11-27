"""Example code for replace-type-code-with-class with name conflict."""


class BloodGroup:
    """Existing class with the name we want to use."""

    def __init__(self, name):
        self.name = name


class Person:
    O = 0
    A = 1
    B = 2
    AB = 3

    def __init__(self, blood_group):
        self.blood_group = blood_group
