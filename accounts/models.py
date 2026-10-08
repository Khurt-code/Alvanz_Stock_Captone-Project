from django.contrib.auth.models import AbstractUser
from django.db import models


# Shared user model: role properties are consumed by report guards and stock-viewer middleware.
class User(AbstractUser):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        CASHIER = "cashier", "Cashier"
        STAFF = "staff", "Staff"
        STOCK_VIEWER = "stock_viewer", "Stock Viewer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER or self.is_superuser

    @property
    def is_cashier(self):
        return self.role in (self.Role.MANAGER, self.Role.CASHIER)

    @property
    def is_stock_viewer(self):
        return self.role == self.Role.STOCK_VIEWER

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"