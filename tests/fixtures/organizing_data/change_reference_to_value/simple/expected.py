class Currency:
    def __init__(self, code):
        self.code = code

    def __eq__(self, other):
        if not isinstance(other, Currency):
            return False
        return self.code == other.code

    def __hash__(self):
        return hash(self.code)
