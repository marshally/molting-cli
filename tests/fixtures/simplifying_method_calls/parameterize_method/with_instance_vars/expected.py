class InventoryItem:
    def __init__(self, quantity, threshold):
        self.quantity = quantity
        self.low_stock_threshold = threshold
        self.critical_stock_threshold = threshold // 2
        self.reorder_pending = False

    def mark_stock_level(self, threshold):
        if self.quantity <= threshold:
            self.reorder_pending = True

    def mark_low_stock(self):
        self.mark_stock_level(self.low_stock_threshold)

    def mark_critical_stock(self):
        self.mark_stock_level(self.critical_stock_threshold)
