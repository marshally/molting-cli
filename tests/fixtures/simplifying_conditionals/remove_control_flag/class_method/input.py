class SecurityChecker:
    def check(self, people):
        found = False
        for person in people:
            if not found:
                if person == "Don":
                    found = True
        return found
