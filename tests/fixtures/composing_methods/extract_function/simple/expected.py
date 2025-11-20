def normalize_string(data):
    return data.strip().lower().replace(" ", "_")


class DataProcessor:
    def process(self, data):
        return normalize_string(data)
