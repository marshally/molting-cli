class Person:
    def __init__(self, name):
        self.name = name
        self.last_name = name.split()[-1]


class Employee(Person):
    def __init__(self, name):
        super().__init__(name)
