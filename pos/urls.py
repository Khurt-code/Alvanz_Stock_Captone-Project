from django.urls import path

from . import views

# POS route names connect checkout, receipts, sales history, and reports to their views.
urlpatterns = [
    path("pos/", views.pos_screen, name="pos_screen"),
    path("pos/checkout/", views.pos_checkout, name="pos_checkout"),
    path("receipt/<int:pk>/", views.sale_receipt, name="sale_receipt"),
    path("sales/<int:pk>/return/", views.sale_return, name="sale_return"),
    path("returns/<int:pk>/receipt/", views.return_receipt, name="return_receipt"),
    path("sales/", views.sales_list, name="sales_list"),
    path("reports/sales/", views.sales_report, name="sales_report"),
    path("reports/inventory/", views.inventory_report, name="inventory_report"),
    path("reports/analytics/", views.analytics_report, name="analytics_report"),
    path("reports/analytics/data/", views.analytics_data, name="analytics_data"),
    path("reports/analytics/export/", views.analytics_export, name="analytics_export"),
]