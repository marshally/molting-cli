"""Example code for push-down-method with decorators."""


class Employee:
    @classmethod
    def create_from_config(cls, config):
        """Create employee from configuration."""
        return cls(config['name'], config['id'])


class Salesman(Employee):
    pass


class Engineer(Employee):
    pass
