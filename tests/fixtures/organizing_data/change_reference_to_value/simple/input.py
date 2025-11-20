class Currency:
    _instances = {}

    def __init__(self, code):
        self.code = code

    @classmethod
    def get(cls, code):
        if code not in cls._instances:
            cls._instances[code] = Currency(code)
        return cls._instances[code]
