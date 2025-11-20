class Order:
    def __init__(self, customer_age):
        self.customer_age = customer_age

    def get_discount(self):
        if self.customer_age > 65:
            discount_rate = 0.1
        else:
            discount_rate = 0.05
        return discount_rate
