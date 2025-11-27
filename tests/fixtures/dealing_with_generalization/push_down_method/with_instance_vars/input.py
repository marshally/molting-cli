class Employee:
    def __init__(self, name, base_salary):
        self.name = name
        self.base_salary = base_salary
        self.performance_rating = 0

    def calculate_bonus(self):
        return self.base_salary * 0.1 * self.performance_rating


class Salesman(Employee):
    def __init__(self, name, base_salary, region):
        super().__init__(name, base_salary)
        self.region = region


class Engineer(Employee):
    def __init__(self, name, base_salary, specialty):
        super().__init__(name, base_salary)
        self.specialty = specialty
