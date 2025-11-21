class Security:
    def __init__(self):
        self.intruders = ["Don", "John", "Alice"]

    def get_and_remove_intruder(self, people):
        """Returns found intruder and sends alert, modifying state."""
        for i, person in enumerate(people):
            if person in self.intruders:
                self._send_alert(person)
                # Remove from list
                self.intruders.pop(i)
                return person
        return ""

    def _send_alert(self, person):
        """Send alert for an intruder."""
        pass
