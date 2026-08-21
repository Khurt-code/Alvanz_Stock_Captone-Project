from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("low-stock/", views.low_stock, name="low_stock"),
    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    # Stock
    path("stock/new/", views.stock_transaction_create, name="stock_transaction_create"),
    path("stock/<int:pk>/delete/", views.stock_transaction_delete, name="stock_transaction_delete"),
    path("stock/", views.stock_transaction_list, name="stock_transaction_list"),
]