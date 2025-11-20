class Security:
    def __init__(self):
        self.intruders = []

    def get_and_remove_intruder(self):
        if len(self.intruders) > 0:
            intruder = self.intruders[0]
            self.intruders.pop(0)
            return intruder
        return None
