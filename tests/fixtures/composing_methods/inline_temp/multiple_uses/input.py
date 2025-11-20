def calculate_discount(price, discount_percent):
    base_price = price * 1.1
    discounted = base_price * discount_percent
    return base_price + discounted
