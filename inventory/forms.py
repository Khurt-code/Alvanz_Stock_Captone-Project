from django import forms

from inventory.models import Product, StockTransaction


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "category", "unit", "cost_price", "sell_price", "min_stock_level", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Portland Cement 40kg"}),
            "sku": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. CEM-40KG"}),
            "unit": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. pcs, bag, liter"}),
            "category": forms.Select(attrs={"class": "input"}),
            "cost_price": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "sell_price": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "min_stock_level": forms.NumberInput(attrs={"class": "input"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = __import__("inventory.models", fromlist=["Category"]).Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Category name"}),
            "description": forms.Textarea(attrs={"class": "input", "rows": 3}),
        }


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["product", "transaction_type", "quantity", "reference", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "input"}),
            "transaction_type": forms.Select(attrs={"class": "input"}),
            "quantity": forms.NumberInput(attrs={"class": "input", "min": 1}),
            "reference": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. SUP-0001"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        qty = cleaned.get("quantity")
        ttype = cleaned.get("transaction_type")
        if product and ttype != StockTransaction.Type.STOCK_IN and qty and qty > product.quantity:
            raise forms.ValidationError(
                f"Stock out/adjustment of {qty} exceeds current stock ({product.quantity} available)."
            )
        return cleaned