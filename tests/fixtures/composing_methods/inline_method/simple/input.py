"""Example code for simple inline method test."""


class Person:
    def __init__(self, late_deliveries):
        self.late_deliveries = late_deliveries

    def get_rating(self):
        return 2 if self.more_than_five_late_deliveries() else 1

    def more_than_five_late_deliveries(self):
        return self.late_deliveries > 5
