"""Example code for replace-parameter-with-explicit-methods with decorators."""


def validate(func):
    """Decorator to validate inputs."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


class Configuration:
    def __init__(self):
        self.timeout = 30
        self.retries = 3

    @validate
    def set_timeout(self, value):
        self.timeout = value

    @validate
    def set_retries(self, value):
        self.retries = value
