"""Example code for encapsulate-collection with multiple call sites."""


class Person:
    def __init__(self):
        self.courses = []

    def get_courses(self):
        return self.courses


class University:
    def __init__(self):
        self.students = []

    def add_student(self, person):
        self.students.append(person)

    def print_all_courses(self):
        for student in self.students:
            # Multiple accesses to courses collection
            print(f"Student has {len(student.courses)} courses")
            for course in student.courses:
                print(f"  - {course}")


def count_total_courses(person):
    # Another access to courses collection
    return len(person.courses)


def find_course(person, course_name):
    # Yet another access to courses collection
    for course in person.courses:
        if course == course_name:
            return True
    return False
