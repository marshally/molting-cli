class DataProcessor:
    def process(self, data):
        if self._validate(data):
            return self.transform(data)
        return None

    def transform(self, data):
        clean_data = self._validate(data)
        if clean_data:
            return self._validate(data)
        return data

    def _validate(self, data):
        return data is not None and len(data) > 0
