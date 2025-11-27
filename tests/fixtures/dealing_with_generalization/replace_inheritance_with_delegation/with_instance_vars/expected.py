class DataStore:
    def __init__(self, namespace):
        self._data = {}
        self.namespace = namespace
        self.access_count = 0
        self.modified = False

    def get_value(self, key):
        self.access_count += 1
        full_key = f"{self.namespace}:{key}"
        return self._data.get(full_key)

    def set_value(self, key, value):
        self.access_count += 1
        self.modified = True
        full_key = f"{self.namespace}:{key}"
        self._data[full_key] = value

    def get_stats(self):
        return {
            "namespace": self.namespace,
            "access_count": self.access_count,
            "modified": self.modified,
            "size": len(self._data),
        }
