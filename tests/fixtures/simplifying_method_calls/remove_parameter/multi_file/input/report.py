from order import Order


def generate_order_report(orders):
    totals = []
    for order_data in orders:
        order = Order(order_data['items'])
        total = order.calculate_total(
            order_data['quantity'],
            order_data['price'],
            order_data.get('discount_code')
        )
        totals.append(total)
    return sum(totals)
