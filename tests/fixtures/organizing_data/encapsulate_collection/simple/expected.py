class Person:
    def __init__(self):
        self._courses = []

    def get_courses(self):
        return tuple(self._courses)

    def add_course(self, course):
        self._courses.append(course)

    def remove_course(self, course):
        self._courses.remove(course)
