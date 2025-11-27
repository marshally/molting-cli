"""Example code for encapsulate-field with multiple call sites."""


class Person:
    def __init__(self, name):
        self.name = name


class Team:
    def __init__(self):
        self.members = []

    def add_member(self, person):
        self.members.append(person)

    def print_roster(self):
        for person in self.members:
            # Multiple accesses to person.name
            print(f"Team member: {person.name}")


def greet_person(person):
    # Another access to person.name
    print(f"Hello, {person.name}!")


def get_initials(person):
    # Yet another access to person.name
    parts = person.name.split()
    return "".join([p[0] for p in parts])
