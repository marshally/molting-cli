"""Expected output after remove-control-flag with instance variables."""


class SecurityChecker:
    def __init__(self, alert_names):
        self.alert_names = alert_names

    def check_security(self, people):
        for person in people:
            if person in self.alert_names:
                self.send_alert(person)
                return

    def send_alert(self, person):
        pass
