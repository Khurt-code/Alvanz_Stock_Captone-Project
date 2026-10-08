"""Adds Product.image so product forms and POS templates can store and display uploads."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image",
            field=models.ImageField(blank=True, upload_to="products/"),
        ),
    ]