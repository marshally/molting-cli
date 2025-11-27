"""Example code for push-down-method with name conflict."""


class Employee:
    def get_quota(self):
        # Method to be pushed down
        return 0


class Salesman(Employee):
    def get_quota(self):
        # Method already exists in target subclass
        return 1000


class Engineer(Employee):
    pass
