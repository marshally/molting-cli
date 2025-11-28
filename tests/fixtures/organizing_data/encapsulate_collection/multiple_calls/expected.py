"""Example code for encapsulate-collection with multiple call sites."""


class Person:
    def __init__(self):
        self._courses = []

    def get_courses(self):
        return tuple(self._courses)

    def add_course(self, course):
        self._courses.append(course)

    def remove_course(self, course):
        self._courses.remove(course)


class University:
    def __init__(self):
        self.students = []

    def add_student(self, person):
        self.students.append(person)

    def print_all_courses(self):
        for student in self.students:
            # Multiple accesses to courses collection
            print(f"Student has {len(student.get_courses())} courses")
            for course in student.get_courses():
                print(f"  - {course}")


def count_total_courses(person):
    # Another access to courses collection
    return len(person.get_courses())


def find_course(person, course_name):
    # Yet another access to courses collection
    for course in person.get_courses():
        if course == course_name:
            return True
    return False
