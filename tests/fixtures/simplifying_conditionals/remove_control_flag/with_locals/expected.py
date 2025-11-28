"""Example code for remove control flag with local variables."""


def find_matching_product(products, target_price, target_category):
    result = None
    count = 0

    for product in products:
        count += 1
        if product.price <= target_price and product.category == target_category:
            result = product
            return result, count
        if product.is_featured:
            log_featured(product)

    return result, count


def log_featured(product):
    pass
