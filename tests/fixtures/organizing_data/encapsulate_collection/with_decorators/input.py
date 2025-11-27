"""Example code for encapsulate-collection with decorators."""


class Person:
    def __init__(self, name):
        self.name = name
        self.courses = []

    @property
    def course_count(self):
        """Return the number of courses."""
        return len(self.courses)

    @staticmethod
    def create_student(name):
        """Create a new student."""
        return Person(name)

    def get_courses(self):
        return self.courses

    def is_enrolled_in(self, course_name):
        """Check if enrolled in a course."""
        return course_name in self.courses
