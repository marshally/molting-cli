class BloodGroup:
    def __init__(self, code):
        self._code = code


BloodGroup.O = BloodGroup(0)
BloodGroup.A = BloodGroup(1)
BloodGroup.B = BloodGroup(2)
BloodGroup.AB = BloodGroup(3)


class Person:
    def __init__(self, blood_group):
        self.blood_group = blood_group
