class Employee:
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.base_salary = 1000
        self.bonus = 500

    def pay_amount(self):
        raise NotImplementedError()


class Engineer(Employee):

    def pay_amount(self):
        return self.base_salary


class Manager(Employee):

    def pay_amount(self):
        return self.base_salary + self.bonus


class Intern(Employee):

    def pay_amount(self):
        return self.base_salary * 0.5
