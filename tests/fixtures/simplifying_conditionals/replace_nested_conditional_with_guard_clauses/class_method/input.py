class Order:
    def get_discount(self, is_dead, is_separated, is_retired):
        if is_dead:
            result = 10
        else:
            if is_separated:
                result = 20
            else:
                if is_retired:
                    result = 30
                else:
                    result = 5
        return result
