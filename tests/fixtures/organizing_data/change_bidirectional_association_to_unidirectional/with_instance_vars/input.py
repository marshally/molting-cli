"""Example code for change-bidirectional-association-to-unidirectional with instance variables."""


class Project:
    def __init__(self, name, owner):
        self.name = name
        self._owner = None
        self.task_count = 0
        self.set_owner(owner)

    def set_owner(self, owner):
        if self._owner is not None:
            self._owner.remove_project(self)
        self._owner = owner
        if owner is not None:
            owner.add_project(self)

    def add_task(self):
        self.task_count += 1


class Owner:
    def __init__(self, username):
        self.username = username
        self._projects = set()
        self.active = True

    def add_project(self, project):
        self._projects.add(project)

    def remove_project(self, project):
        self._projects.discard(project)
