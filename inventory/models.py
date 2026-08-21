from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    unit = models.CharField(max_length=20, default="pcs")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock_level

    def __str__(self):
        return f"{self.name} ({self.sku})"


class StockTransaction(models.Model):
    class Type(models.TextChoices):
        STOCK_IN = "IN", "Stock In"
        STOCK_OUT = "OUT", "Stock Out"
        ADJUST = "ADJ", "Adjustment"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=5, choices=Type.choices)
    quantity = models.PositiveIntegerField()
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="stock_transactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.quantity} x {self.product}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating:
            self.apply_to_stock()

    def apply_to_stock(self):
        product = self.product
        if self.transaction_type == self.Type.STOCK_IN:
            product.quantity += self.quantity
        else:
            product.quantity = max(0, product.quantity - self.quantity)
        product.save(update_fields=["quantity", "updated_at"])

    def delete(self, *args, **kwargs):
        self.reverse_stock()
        super().delete(*args, **kwargs)

    def reverse_stock(self):
        product = self.product
        if self.transaction_type == self.Type.STOCK_IN:
            product.quantity = max(0, product.quantity - self.quantity)
        else:
            product.quantity += self.quantity
        product.save(update_fields=["quantity", "updated_at"])