class InventoryItem:
    def __init__(self, quantity, threshold):
        self.quantity = quantity
        self.low_stock_threshold = threshold
        self.critical_stock_threshold = threshold // 2
        self.reorder_pending = False

    def mark_low_stock(self):
        if self.quantity <= self.low_stock_threshold:
            self.reorder_pending = True

    def mark_critical_stock(self):
        if self.quantity <= self.critical_stock_threshold:
            self.reorder_pending = True
