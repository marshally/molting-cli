class Order:
    def __init__(self, customer_age):
        self.customer_age = customer_age

    def get_discount(self):
        if is_senior(self):
            discount_rate = senior_discount_rate()
        else:
            discount_rate = regular_discount_rate()
        return discount_rate


def is_senior(self):
    return self.customer_age > 65


def senior_discount_rate():
    return 0.1


def regular_discount_rate():
    return 0.05
