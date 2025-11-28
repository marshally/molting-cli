"""Expected output after change-unidirectional-association-to-bidirectional with instance variables."""


class Team:
    def __init__(self, name, manager):
        self._manager = None
        self.set_manager(manager)

    def add_member(self):
        self.member_count += 1

    def set_manager(self, manager):
        if self._manager is not None:
            self._manager.remove_team(self)
        self._manager = manager
        if manager is not None:
            manager.add_team(self)


class Manager:
    def __init__(self, name):
        self.name = name
        self.years_experience = 0

    def add_team(self, team):
        self._teams.add(team)

    def remove_team(self, team):
        self._teams.discard(team)
