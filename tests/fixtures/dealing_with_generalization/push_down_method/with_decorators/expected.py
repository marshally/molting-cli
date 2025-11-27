"""Example code for push-down-method with decorators."""


class Employee:
    pass


class Salesman(Employee):
    @classmethod
    def create_from_config(cls, config):
        """Create employee from configuration."""
        return cls(config['name'], config['id'])


class Engineer(Employee):
    pass
