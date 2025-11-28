"""Example code for replace-type-code-with-class with multiple call sites."""


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

    def get_blood_group_name(self):
        if self.blood_group == BloodGroup.O:
            return "O"
        elif self.blood_group == BloodGroup.A:
            return "A"
        elif self.blood_group == BloodGroup.B:
            return "B"
        elif self.blood_group == BloodGroup.AB:
            return "AB"


class BloodBank:
    def __init__(self):
        self.donors = []

    def add_donor(self, person):
        self.donors.append(person)

    def find_compatible_donors(self, recipient):
        compatible = []
        for donor in self.donors:
            # Multiple accesses to blood_group
            if recipient.blood_group == BloodGroup.AB:
                # AB can receive from anyone
                compatible.append(donor)
            elif recipient.blood_group == donor.blood_group:
                # Same blood type is always compatible
                compatible.append(donor)
        return compatible


def is_universal_donor(person):
    # Another access to blood_group
    return person.blood_group == BloodGroup.O


def can_donate_to(donor, recipient):
    # Yet another access to blood_group
    if donor.blood_group == BloodGroup.O:
        return True
    return donor.blood_group == recipient.blood_group
