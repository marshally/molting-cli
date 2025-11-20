class Party:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name


class Employee(Party):
    def __init__(self, name, id, annual_cost):
        super().__init__(name)
        self.id = id
        self.annual_cost = annual_cost

    def get_id(self):
        return self.id


class Department(Party):
    def __init__(self, name, staff):
        super().__init__(name)
        self.staff = staff

    def get_total_annual_cost(self):
        return sum(s.annual_cost for s in self.staff)
