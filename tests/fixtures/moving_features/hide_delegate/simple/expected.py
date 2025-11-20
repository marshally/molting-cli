class Person:
    def __init__(self, department):
        self._department = department

    def get_manager(self):
        return self._department.manager


class Department:
    def __init__(self, manager):
        self.manager = manager
