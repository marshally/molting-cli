class IntervalWindow:
    def __init__(self):
        self.start_field = ""
        self.end_field = ""
        self.length_field = ""

    def start_field_focus_lost(self):
        self.calculate_length()

    def calculate_length(self):
        start = int(self.start_field)
        end = int(self.end_field)
        length = end - start
        self.length_field = str(length)
