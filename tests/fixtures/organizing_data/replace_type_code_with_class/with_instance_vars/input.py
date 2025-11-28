"""Example code for replace-type-code-with-class with instance variables."""


class Task:
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3

    def __init__(self, title, priority):
        self.title = title
        self.priority = priority
        self.completed = False

    def mark_complete(self):
        self.completed = True

    def is_high_priority(self):
        return self.priority >= self.HIGH
