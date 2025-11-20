class Order:
    def get_discount(self, is_dead, is_separated, is_retired):
        if is_dead:
            return 10
        if is_separated:
            return 20
        if is_retired:
            return 30
        return 5
