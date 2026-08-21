from django.db import models, transaction


class Sale(models.Model):
    receipt_no = models.CharField(max_length=20, unique=True, editable=False)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_tendered = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cashier = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="sales")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.receipt_no} - {self.total}"

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = self._generate_receipt_no()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_receipt_no():
        from datetime import date

        prefix = "R" + date.today().strftime("%Y%m%d")
        last = Sale.objects.filter(receipt_no__startswith=prefix).order_by("-receipt_no").first()
        seq = int(last.receipt_no[-4:]) + 1 if last else 1
        return f"{prefix}{seq:04d}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.CASCADE, related_name="sale_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


def record_sale(cart, cashier, cash_tendered, discount=0):
    """cart: list of (product, quantity). Atomically processes a sale."""
    from inventory.models import StockTransaction

    with transaction.atomic():
        subtotal = 0
        for product, qty in cart:
            if qty < 1 or product.quantity < qty:
                raise ValueError(f"Not enough stock for {product.name}")
            subtotal += product.sell_price * qty

        total = subtotal - discount
        change = max(0, cash_tendered - total)
        sale = Sale.objects.create(
            subtotal=subtotal,
            discount=discount,
            total=total,
            cash_tendered=cash_tendered,
            change=change,
            cashier=cashier,
        )

        for product, qty in cart:
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=qty,
                unit_price=product.sell_price,
                subtotal=product.sell_price * qty,
            )
            StockTransaction.objects.create(
                product=product,
                transaction_type=StockTransaction.Type.STOCK_OUT,
                quantity=qty,
                reference=sale.receipt_no,
                notes=f"POS sale {sale.receipt_no}",
                user=cashier,
            )
        return sale