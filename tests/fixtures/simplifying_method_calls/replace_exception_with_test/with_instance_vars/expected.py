class DataStore:
    def __init__(self):
        self.values = []
        self.default_value = 0


def get_value_at_index(store, index):
    if index >= len(store.values):
        return store.default_value
    return store.values[index]
