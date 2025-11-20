"""Expected output after simple inline method refactoring."""


class Person:
    def __init__(self, late_deliveries):
        self.late_deliveries = late_deliveries

    def get_rating(self):
        return 2 if self.late_deliveries > 5 else 1
