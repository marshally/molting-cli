"""Expected output after remove-control-flag with instance variables."""


class SecurityChecker:
    def __init__(self, alert_names):
        self.alert_names = alert_names

    def check_security(self, people):
        found = False
        for person in people:
            if not found:
                if person in self.alert_names:
                    self.send_alert(person)
                    found = True

    def send_alert(self, person):
        pass
