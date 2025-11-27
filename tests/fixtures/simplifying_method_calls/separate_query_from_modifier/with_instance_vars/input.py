class Inventory:
    def __init__(self):
        self.items = []
        self.total_value = 0
        self.last_updated = None

    def get_and_update_lowest_stock(self):
        if len(self.items) > 0:
            lowest = min(self.items, key=lambda x: x.stock)
            lowest.reorder_pending = True
            self.last_updated = "now"
            return lowest
        return None
