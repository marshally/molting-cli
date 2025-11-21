class Employee:
    def __init__(self, name):
        self.name = name


class Salesman(Employee):
    def get_quota(self):
        return 100


class Engineer(Employee):
    pass
