"""Expected output after change-value-to-reference with instance variables."""


class ShoppingCart:
    def __init__(self, product_id):
        self.product = Product.get_named(product_id)
        self.quantity = 0
        self.discount = 0.0

    def add_quantity(self, amount):
        self.quantity += amount

    def apply_discount(self, discount):
        self.discount = discount

    def get_total(self):
        base_price = self.product.price * self.quantity
        return base_price * (1 - self.discount)


class Product:
    _instances = {}

    def __init__(self, product_id):
        self.product_id = product_id
        self.price = 10.0

    @classmethod
    def get_named(cls, product_id):
        if product_id not in cls._instances:
            cls._instances[product_id] = Product(product_id)
        return cls._instances[product_id]
