from django.contrib import admin

from .models import Category, Product, StockTransaction


class StockTransactionInline(admin.TabularInline):
    model = StockTransaction
    extra = 0
    readonly_fields = ("transaction_type", "quantity", "reference", "user", "created_at")
    can_delete = False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "product_count")
    search_fields = ("name",)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "quantity", "min_stock_level", "sell_price", "is_low_stock")
    list_filter = ("category", "is_active", "min_stock_level")
    search_fields = ("name", "sku")
    list_editable = ("quantity", "min_stock_level", "sell_price")
    inlines = [StockTransactionInline]


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("product", "transaction_type", "quantity", "reference", "user", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("product__name", "product__sku", "reference")