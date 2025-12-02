class Calculator:
    def __init__(self):
        self.history = []

    def calculate(self, x, y, precision=2):
        result = x + y
        if precision is not None:
            result = round(result, precision)
        self.history.append(result)
        return result

    def get_history(self):
        return self.history
