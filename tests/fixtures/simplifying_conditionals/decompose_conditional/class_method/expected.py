class Order:
    def __init__(self, customer_age):
        self.customer_age = customer_age

    def get_discount(self):
        if is_winter(self):
            discount_rate = winter_charge()
        else:
            discount_rate = summer_charge()
        return discount_rate


def is_winter(self):
    return self.customer_age > 65


def winter_charge():
    return 0.1


def summer_charge():
    return 0.05
