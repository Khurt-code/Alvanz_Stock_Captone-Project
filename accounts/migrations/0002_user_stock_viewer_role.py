"""Adds the Stock Viewer choice required by accounts.User and its access middleware."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("manager", "Manager"),
                    ("cashier", "Cashier"),
                    ("staff", "Staff"),
                    ("stock_viewer", "Stock Viewer"),
                ],
                default="staff",
                max_length=20,
            ),
        ),
    ]