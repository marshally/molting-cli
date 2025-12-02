"""Invoice generator for products."""

from product import Product


class InvoiceGenerator:
    """Generate invoices for product sales."""

    def __init__(self, tax_rate=0.1):
        self.tax_rate = tax_rate

    def generate_invoice(self, product, quantity):
        """Generate an invoice for a product purchase."""
        subtotal = product.price * quantity
        tax = subtotal * self.tax_rate
        total = subtotal + tax
        return {
            "product": product.name,
            "unit_price": product.price,
            "quantity": quantity,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }

    def apply_bulk_discount(self, product, quantity):
        """Apply bulk discount if quantity is high."""
        if quantity >= 10:
            # Modify price directly for bulk orders
            original_price = product.price
            product.price = original_price * 0.9
            return original_price - product.price
        return 0
