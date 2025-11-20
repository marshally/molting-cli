class DataProcessor:
    def process(self, data):
        # format the data
        formatted = data.strip().lower().replace(" ", "_")
        return formatted
