"""Example code for encapsulate-field with decorators."""


class Person:
    def __init__(self, name, age):
        self._name = name
        self.age = age

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def is_adult(self):
        """Check if person is an adult."""
        return self.age >= 18

    @classmethod
    def from_birth_year(cls, name, birth_year):
        """Create a person from birth year."""
        import datetime

        current_year = datetime.datetime.now().year
        age = current_year - birth_year
        return cls(name, age)

    def greet(self):
        return f"Hello, my name is {self.name}"
