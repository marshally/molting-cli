"""Example code for remove control flag with decorators."""


class SecurityChecker:
    def __init__(self, people):
        self.people = people

    @property
    def is_secure(self):
        found = False
        for person in self.people:
            if not found:
                if person == "Don":
                    self.send_alert()
                    found = True
                if person == "John":
                    self.send_alert()
                    found = True
        return not found

    def send_alert(self):
        pass
