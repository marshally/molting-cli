class Security:
    def __init__(self):
        self.intruders = ["Don", "John", "Alice"]

    def get_and_remove_intruder(self, people):
        """Returns found intruder and sends alert, modifying state."""
        for i, person in enumerate(people):
            if person in self.intruders:
                return person
        return ""

    def alert_for_intruder(self, people):
        found = self.get_and_remove_intruder(people)
        if found:
            self._send_alert(found)

    def _send_alert(self, person):
        """Send alert for an intruder."""
        pass
