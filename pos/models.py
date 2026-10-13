from decimal import Decimal

from django.db import models, transaction


# Sales data layer; record_sale atomically links Sale/SaleItem records to inventory stock-out transactions.
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

    @property
    def returned_quantity(self):
        return self.return_items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def returnable_quantity(self):
        return max(0, self.quantity - self.returned_quantity)


class Return(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash Refund"
        CREDIT = "credit", "Store Credit"

    receipt_no = models.CharField(max_length=20, unique=True, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="returns")
    reason = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    processed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="returns_processed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.receipt_no} - {self.refund_amount}"

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = self._generate_receipt_no()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_receipt_no():
        from datetime import date

        prefix = "RC" + date.today().strftime("%Y%m%d")
        last = Return.objects.filter(receipt_no__startswith=prefix).order_by("-receipt_no").first()
        seq = int(last.receipt_no[-4:]) + 1 if last else 1
        return f"{prefix}{seq:04d}"


class ReturnItem(models.Model):
    return_ref = models.ForeignKey(Return, on_delete=models.CASCADE, related_name="items")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name="return_items")
    product = models.ForeignKey("inventory.Product", on_delete=models.CASCADE, related_name="return_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    restock = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


def record_sale(cart, cashier, cash_tendered, discount=0):
    """cart: list of (product, quantity). Atomically processes a sale."""
    from inventory.models import StockTransaction
    from inventory.realtime import broadcast_event

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
        transaction.on_commit(lambda: broadcast_event("sale"))
        return sale


def record_return(sale, lines, processed_by, reason="", refund_method=Return.Method.CASH):
    """lines: list of (sale_item, quantity, restock). Atomically processes a return."""
    from inventory.models import StockTransaction
    from inventory.realtime import broadcast_event

    if not lines:
        raise ValueError("Select at least one item to return.")

    with transaction.atomic():
        # Discount is spread proportionally so refunds reflect the price actually paid.
        factor = (sale.total / sale.subtotal) if sale.subtotal else Decimal("0")
        refund_amount = Decimal("0")
        for sale_item, qty, restock in lines:
            if qty < 1:
                raise ValueError(f"Invalid return quantity for {sale_item.product.name}.")
            if qty > sale_item.returnable_quantity:
                raise ValueError(
                    f"Only {sale_item.returnable_quantity} of '{sale_item.product.name}' "
                    f"can still be returned."
                )
            refund_amount += (sale_item.unit_price * qty * factor).quantize(Decimal("0.01"))

        ret = Return.objects.create(
            sale=sale,
            reason=reason,
            refund_amount=refund_amount,
            refund_method=refund_method,
            processed_by=processed_by,
        )

        for sale_item, qty, restock in lines:
            line_subtotal = (sale_item.unit_price * qty * factor).quantize(Decimal("0.01"))
            ReturnItem.objects.create(
                return_ref=ret,
                sale_item=sale_item,
                product=sale_item.product,
                quantity=qty,
                unit_price=sale_item.unit_price,
                subtotal=line_subtotal,
                restock=restock,
            )
            if restock:
                StockTransaction.objects.create(
                    product=sale_item.product,
                    transaction_type=StockTransaction.Type.STOCK_IN,
                    quantity=qty,
                    reference=ret.receipt_no,
                    notes=f"Return {ret.receipt_no} (sale {sale.receipt_no})",
                    user=processed_by,
                )
        transaction.on_commit(lambda: broadcast_event("return"))
        return ret