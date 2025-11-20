class Employee:
    @staticmethod
    def create(employee_type):
        if employee_type == "ENGINEER":
            return Engineer()
        elif employee_type == "SALESMAN":
            return Salesman()
        elif employee_type == "MANAGER":
            return Manager()


class Engineer(Employee):
    pass


class Salesman(Employee):
    pass


class Manager(Employee):
    pass
