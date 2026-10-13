from django.contrib import admin

from .models import Return, ReturnItem, Sale, SaleItem


# Connects sales and their line items to Django Admin for authorized review.
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


# Returns and their line items are review-only records in admin.
class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    readonly_fields = ("sale_item", "product", "quantity", "unit_price", "subtotal", "restock")
    can_delete = False


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "sale", "refund_amount", "refund_method", "processed_by", "created_at")
    list_filter = ("refund_method", "created_at")
    search_fields = ("receipt_no", "sale__receipt_no", "processed_by__username")
    inlines = [ReturnItemInline]
    readonly_fields = ("receipt_no", "sale", "refund_amount", "processed_by", "created_at")