class Calculator:
    def __init__(self):
        self.history = []

    def calculate(self, x, y):
        result = x + y
        self.history.append(result)
        return result

    def get_history(self):
        return self.history
