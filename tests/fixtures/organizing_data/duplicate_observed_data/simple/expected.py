class Interval:
    def __init__(self):
        self.start = 0
        self.end = 0
        self.length = 0

    def calculate_length(self):
        self.length = self.end - self.start


class IntervalWindow:
    def __init__(self):
        self.interval = Interval()
        self.start_field = ""
        self.end_field = ""
        self.length_field = ""
        self.update()

    def start_field_focus_lost(self):
        self.interval.start = int(self.start_field)
        self.calculate_length()

    def calculate_length(self):
        self.interval.calculate_length()
        self.update()

    def update(self):
        self.start_field = str(self.interval.start)
        self.end_field = str(self.interval.end)
        self.length_field = str(self.interval.length)
