import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from functools import wraps

from inventory.models import Product

from .models import Sale, record_sale


def manager_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, "You don't have permission to view Sales & Reports.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


@login_required
def pos_screen(request):
    products = Product.objects.filter(is_active=True).order_by("name")
    categories = {}
    for p in products:
        categories.setdefault(p.category.name if p.category else "Uncategorized", []).append(p)
    context = {
        "categories": categories,
        "products": products,
        "cash_multiplier": settings.POS_CASH_MULTIPLIER,
        "low_stock_products": Product.objects.filter(is_active=True, quantity__lte=F("min_stock_level")),
    }
    return render(request, "pos/pos_screen.html", context)


@require_POST
@login_required
def pos_checkout(request):
    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        cash = Decimal(str(data.get("cash", 0)))
        discount = Decimal(str(data.get("discount", 0)))
        if not items:
            return JsonResponse({"error": "Cart is empty."}, status=400)

        cart = []
        for item in items:
            product = get_object_or_404(Product, pk=item.get("id"), is_active=True)
            qty = int(item.get("qty", 0))
            if qty < 1:
                return JsonResponse({"error": f"Invalid quantity for {product.name}."}, status=400)
            if qty > product.quantity:
                return JsonResponse(
                    {"error": f"Only {product.quantity} of '{product.name}' in stock."}, status=400
                )
            cart.append((product, qty))

        subtotal = sum(p.sell_price * q for p, q in cart)
        if discount > subtotal:
            return JsonResponse({"error": "Discount cannot exceed subtotal."}, status=400)
        total = subtotal - discount
        if cash < total:
            return JsonResponse({"error": "Insufficient cash tendered."}, status=400)
        max_cash = total * Decimal(str(settings.POS_CASH_MULTIPLIER))
        if cash > max_cash:
            return JsonResponse(
                {"error": f"Cash tendered exceeds the limit of {settings.POS_CASH_MULTIPLIER}x the total (max ₱{max_cash:.2f})."},
                status=400,
            )

        sale = record_sale(cart, request.user, cash_tendered=cash, discount=discount)
        return JsonResponse({"success": True, "receipt_no": sale.receipt_no, "sale_id": sale.id})
    except (ValueError, TypeError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {e}"}, status=400)


@login_required
def sale_receipt(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related("items__product"), pk=pk)
    return render(request, "pos/receipt.html", {"sale": sale})


@manager_required
def sales_list(request):
    sales = Sale.objects.select_related("cashier").prefetch_related("items__product")
    start = request.GET.get("from", "").strip()
    end = request.GET.get("to", "").strip()
    error = ""
    if start and end and start > end:
        error = "The 'from' date cannot be later than the 'to' date."
        start = end = ""
    if start:
        sales = sales.filter(created_at__date__gte=start)
    if end:
        sales = sales.filter(created_at__date__lte=end)
    sales = sales.order_by("-created_at")
    total = sum(s.total for s in sales)
    context = {
        "sales": sales,
        "total": total,
        "start": start,
        "end": end,
        "filter_active": bool(start or end),
        "filter_error": error,
    }
    return render(request, "pos/sales_list.html", context)


@manager_required
def sales_report(request):
    period = request.GET.get("period", "today")
    now = timezone.now()
    date_ranges = {
        "today": (now.date(), now.date()),
        "week": (now.date() - timedelta(days=6), now.date()),
        "month": (now.date().replace(day=1), now.date()),
    }
    start, end = date_ranges.get(period, date_ranges["today"])
    sales = Sale.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    summary = sales.aggregate(
        total=Sum("total"),
        subtotal=Sum("subtotal"),
        discount=Sum("discount"),
        count=Count("id"),
    )
    daily_sales = (
        Sale.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        .extra({"day": "date(created_at)"})
        .values("day")
        .annotate(total=Sum("total"), count=Count("id"))
        .order_by("day")
    )
    return render(
        request,
        "reports/sales_report.html",
        {
"period": period,
        "start": start,
        "end": end,
        "periods": [("Today", "today"), ("Last 7 Days", "week"), ("This Month", "month")],
        "summary": summary,
            "daily_sales": daily_sales,
            "sales": sales[:50],
        },
    )


@manager_required
def inventory_report(request):
    products = Product.objects.select_related("category").filter(is_active=True).order_by("category__name", "name")
    total_cost = sum(p.cost_price * p.quantity for p in products)
    total_value = sum(p.sell_price * p.quantity for p in products)
    return render(
        request,
        "reports/inventory_report.html",
        {"products": products, "total_cost": total_cost, "total_value": total_value},
    )