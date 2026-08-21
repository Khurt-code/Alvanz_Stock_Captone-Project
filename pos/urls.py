from django.urls import path

from . import views

urlpatterns = [
    path("pos/", views.pos_screen, name="pos_screen"),
    path("pos/checkout/", views.pos_checkout, name="pos_checkout"),
    path("receipt/<int:pk>/", views.sale_receipt, name="sale_receipt"),
    path("sales/", views.sales_list, name="sales_list"),
    path("reports/sales/", views.sales_report, name="sales_report"),
    path("reports/inventory/", views.inventory_report, name="inventory_report"),
]