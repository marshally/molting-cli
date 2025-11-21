class Order:
    def get_discount(self, quantity, customer_type, is_vip):
        if quantity < 10:
            return 0.0
        if customer_type == "gold":
            return 0.0
        if is_vip:
            return 0.0
        return 0.05
