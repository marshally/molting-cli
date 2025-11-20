class Employee:
    def __init__(self, base_salary, rating):
        self.base_salary = base_salary
        self.rating = rating

    def calculate_bonus(self):
        return self.base_salary * self.get_bonus_multiplier()

    def get_bonus_multiplier(self):
        # Only used internally
        return 0.1 if self.rating > 8 else 0.05
