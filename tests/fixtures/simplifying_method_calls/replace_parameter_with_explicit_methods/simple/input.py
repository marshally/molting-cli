class Employee:
    HEIGHT = 0
    WIDTH = 1

    def __init__(self):
        self.height = 0
        self.width = 0

    def set_value(self, name, value):
        if name == "height":
            self.height = value
        elif name == "width":
            self.width = value
