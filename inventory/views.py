from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from pos.models import Sale

from .forms import CategoryForm, ProductForm, StockTransactionForm
from .models import Category, Product, StockTransaction


@login_required
def dashboard(request):
    low_stock_products = Product.objects.filter(is_active=True, quantity__lte=F("min_stock_level")).order_by("quantity")
    recent_transactions = StockTransaction.objects.select_related("product", "user")[:10]
    recent_sales = Sale.objects.select_related("cashier")[:10]

    inv = Product.objects.filter(is_active=True).aggregate(
        product_count=Count("id"),
        total_value=Sum(F("quantity") * F("sell_price")),
    )
    sales_total = Sale.objects.aggregate(total=Sum("total"))["total"] or 0

    context = {
        "product_count": inv["product_count"],
        "category_count": Category.objects.count(),
        "total_value": inv["total_value"] or 0,
        "low_stock_count": low_stock_products.count(),
        "low_stock_products": low_stock_products,
        "recent_transactions": recent_transactions,
        "recent_sales": recent_sales,
        "sales_total": sales_total,
    }
    return render(request, "dashboard.html", context)


@login_required
def product_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    products = Product.objects.select_related("category").filter(is_active=True)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    products = products.order_by("name")
    paginator = Paginator(products, 15)
    page = paginator.get_page(request.GET.get("page"))
    context = {
        "products": page,
        "categories": Category.objects.all(),
        "query": query,
        "category_id": category_id,
    }
    return render(request, "inventory/product_list.html", context)


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created.")
            return redirect("product_list")
    else:
        form = ProductForm()
    return render(request, "inventory/product_form.html", {"form": form, "title": "Add Product"})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect("product_detail", pk=pk)
    else:
        form = ProductForm(instance=product)
    return render(request, "inventory/product_form.html", {"form": form, "product": product, "title": "Edit Product"})


@login_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save(update_fields=["is_active"])
    messages.success(request, f"'{product.name}' removed.")
    return redirect("product_list")


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    transactions = product.transactions.select_related("user")[:20]
    return render(request, "inventory/product_detail.html", {"product": product, "transactions": transactions})


@login_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products"))
    return render(request, "inventory/category_list.html", {"categories": categories})


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "inventory/category_form.html", {"form": form, "title": "Add Category"})


@login_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, "Category deleted.")
    return redirect("category_list")


@login_required
def stock_transaction_create(request):
    if request.method == "POST":
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            txn = form.save(commit=False)
            txn.user = request.user
            txn.save()
            messages.success(request, f"{txn.get_transaction_type_display()} of {txn.quantity} recorded.")
            return redirect("product_detail", pk=txn.product_id)
    else:
        form = StockTransactionForm()
    return render(request, "inventory/stock_form.html", {"form": form, "title": "Record Stock Movement"})


@login_required
def stock_transaction_list(request):
    transactions = StockTransaction.objects.select_related("product", "user").all()
    ttype = request.GET.get("type", "")
    if ttype:
        transactions = transactions.filter(transaction_type=ttype)
    paginator = Paginator(transactions, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "inventory/stock_list.html", {"transactions": page, "ttype": ttype})


@login_required
@require_POST
def stock_transaction_delete(request, pk):
    txn = get_object_or_404(StockTransaction, pk=pk)
    label = f"{txn.get_transaction_type_display()} of {txn.quantity} × {txn.product.name}"
    txn.delete()
    messages.success(request, f"Stock movement deleted ({label}). Stock adjusted to compensate.")
    return redirect(request.META.get("HTTP_REFERER") or "stock_transaction_list")


@login_required
def low_stock(request):
    products = (
        Product.objects.select_related("category")
        .filter(is_active=True, quantity__lte=F("min_stock_level"))
        .order_by("quantity")
    )
    return render(request, "inventory/low_stock.html", {"products": products})