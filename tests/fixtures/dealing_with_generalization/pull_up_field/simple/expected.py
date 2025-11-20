class Employee:
    def __init__(self, name):
        self.name = name


class Salesman(Employee):
    def __init__(self, name):
        super().__init__(name)


class Engineer(Employee):
    def __init__(self, name):
        super().__init__(name)
