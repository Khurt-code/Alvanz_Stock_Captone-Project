from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price", "subtotal")
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "cashier", "subtotal", "discount", "total", "created_at")
    list_filter = ("created_at",)
    search_fields = ("receipt_no", "cashier__username")
    inlines = [SaleItemInline]
    readonly_fields = ("receipt_no", "subtotal", "total", "cash_tendered", "change")