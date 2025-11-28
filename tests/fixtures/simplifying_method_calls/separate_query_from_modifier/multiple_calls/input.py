"""Example code for separate-query-from-modifier with multiple call sites."""


class Security:
    def __init__(self):
        self.intruders = ["Hacker1", "Hacker2", "Hacker3"]

    def get_and_remove_intruder(self):
        if self.intruders:
            intruder = self.intruders[0]
            self.intruders.pop(0)
            return intruder
        return ""


class SecurityMonitor:
    def __init__(self, security):
        self.security = security
        self.alerts = []

    def check_threats(self):
        threat = self.security.get_and_remove_intruder()
        if threat:
            self.alerts.append(f"Threat detected: {threat}")

    def process_all_threats(self):
        while True:
            threat = self.security.get_and_remove_intruder()
            if not threat:
                break
            print(f"Processing: {threat}")


def log_intruder(security):
    intruder = security.get_and_remove_intruder()
    if intruder:
        print(f"Logging intruder: {intruder}")


def count_and_clear_intruders(security):
    count = 0
    while True:
        intruder = security.get_and_remove_intruder()
        if not intruder:
            break
        count += 1
    return count
