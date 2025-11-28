"""Example code for replace-type-code-with-class with multiple call sites."""


class Person:
    O = 0
    A = 1
    B = 2
    AB = 3

    def __init__(self, blood_group):
        self.blood_group = blood_group

    def get_blood_group_name(self):
        if self.blood_group == Person.O:
            return "O"
        elif self.blood_group == Person.A:
            return "A"
        elif self.blood_group == Person.B:
            return "B"
        elif self.blood_group == Person.AB:
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
            if recipient.blood_group == Person.AB:
                # AB can receive from anyone
                compatible.append(donor)
            elif recipient.blood_group == donor.blood_group:
                # Same blood type is always compatible
                compatible.append(donor)
        return compatible


def is_universal_donor(person):
    # Another access to blood_group
    return person.blood_group == Person.O


def can_donate_to(donor, recipient):
    # Yet another access to blood_group
    if donor.blood_group == Person.O:
        return True
    return donor.blood_group == recipient.blood_group
