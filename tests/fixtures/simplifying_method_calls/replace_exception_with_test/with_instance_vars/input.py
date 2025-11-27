class DataStore:
    def __init__(self):
        self.values = []
        self.default_value = 0


def get_value_at_index(store, index):
    try:
        return store.values[index]
    except IndexError:
        return store.default_value
