class DataProcessor:
    def process(self, data):
        if self.validate(data):
            return self.transform(data)
        return None

    def transform(self, data):
        clean_data = self.validate(data)
        if clean_data:
            return self.validate(data)
        return data

    def validate(self, data):
        return data is not None and len(data) > 0
