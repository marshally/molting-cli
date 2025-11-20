class Person:
    def __init__(self, name):
        self.name = name
        self.last_name = name.split()[-1]


class Employee:
    def __init__(self, name):
        self._person = Person(name)

    def get_name(self):
        return self._person.name

    def set_name(self, name):
        self._person.name = name

    def get_last_name(self):
        return self._person.last_name
