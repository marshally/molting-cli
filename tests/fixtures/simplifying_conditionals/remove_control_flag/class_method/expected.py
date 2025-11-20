class SecurityChecker:
    def check(self, people):
        for person in people:
            if person == "Don":
                return True
        return False
