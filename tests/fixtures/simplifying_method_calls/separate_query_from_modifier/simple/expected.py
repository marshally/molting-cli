class Security:
    def __init__(self):
        self.intruders = []

    def get_intruder(self):
        if len(self.intruders) > 0:
            return self.intruders[0]
        return None

    def remove_intruder(self):
        if len(self.intruders) > 0:
            self.intruders.pop(0)
