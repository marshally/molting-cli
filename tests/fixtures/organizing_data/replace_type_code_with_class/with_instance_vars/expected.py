"""Expected output after replace-type-code-with-class with instance variables."""


class Priority:
    def __init__(self, code):
        self._code = code


Priority.LOW = Priority(0)
Priority.MEDIUM = Priority(1)
Priority.HIGH = Priority(2)
Priority.URGENT = Priority(3)


class Task:
    def __init__(self, title, priority):
        self.title = title
        self.priority = priority
        self.completed = False

    def mark_complete(self):
        self.completed = True

    def is_high_priority(self):
        return self.priority >= self.HIGH
