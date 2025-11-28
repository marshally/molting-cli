"""Expected output after remove control flag with decorators."""


class SecurityChecker:
    def __init__(self, people):
        self.people = people

    @property
    def is_secure(self):
        for person in self.people:
            if person == "Don":
                self.send_alert()
                return False
            if person == "John":
                self.send_alert()
                return False
        return True

    def send_alert(self):
        pass
