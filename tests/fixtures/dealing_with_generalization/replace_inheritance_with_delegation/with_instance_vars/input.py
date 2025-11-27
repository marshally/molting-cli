class DataStore(dict):
    def __init__(self, namespace):
        super().__init__()
        self.namespace = namespace
        self.access_count = 0
        self.modified = False

    def get_value(self, key):
        self.access_count += 1
        full_key = f"{self.namespace}:{key}"
        return self.get(full_key)

    def set_value(self, key, value):
        self.access_count += 1
        self.modified = True
        full_key = f"{self.namespace}:{key}"
        self[full_key] = value

    def get_stats(self):
        return {
            "namespace": self.namespace,
            "access_count": self.access_count,
            "modified": self.modified,
            "size": len(self),
        }
