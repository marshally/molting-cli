"""Example code for change-bidirectional-association-to-unidirectional with instance variables."""


class Project:
    def __init__(self, name, owner):
        self.name = name
        self.task_count = 0
        self.owner = owner

    def add_task(self):
        self.task_count += 1


class Owner:
    def __init__(self, username):
        self.username = username
        self.active = True
