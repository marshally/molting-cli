class Employee:
    def __init__(self, name, id, annual_cost):
        self.name = name
        self.id = id
        self.annual_cost = annual_cost

    def get_name(self):
        return self.name

    def get_id(self):
        return self.id


class Department:
    def __init__(self, name, staff):
        self.name = name
        self.staff = staff

    def get_name(self):
        return self.name

    def get_total_annual_cost(self):
        return sum(s.annual_cost for s in self.staff)
