"""Example code for change-unidirectional-association-to-bidirectional with instance variables."""


class Team:
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.member_count = 0

    def add_member(self):
        self.member_count += 1


class Manager:
    def __init__(self, name):
        self.name = name
        self.years_experience = 0
