"""Example code for hide-delegate with name conflict."""


class Person:
    def __init__(self, department):
        self.department = department

    def get_manager(self):
        """This method already exists - will conflict with delegating method."""
        return "existing manager"


class Department:
    def __init__(self, manager):
        self.manager = manager
