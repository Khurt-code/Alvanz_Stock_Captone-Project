import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import manager_required
from inventory.models import Product

from .models import Return, Sale, SaleItem, record_return, record_sale


# POS handlers join inventory products to checkout, receipts, and manager-only reporting templates.
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
def sale_return(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related("items__product"), pk=pk)
    if request.method == "POST":
        lines = []
        for item in sale.items.all():
            qty = request.POST.get(f"qty_{item.id}", "0").strip() or "0"
            try:
                qty = int(qty)
            except ValueError:
                qty = 0
            if qty > 0:
                restock = request.POST.get(f"restock_{item.id}") == "on"
                lines.append((item, qty, restock))
        reason = request.POST.get("reason", "").strip()
        method = request.POST.get("refund_method", Return.Method.CASH)
        if method not in Return.Method.values:
            method = Return.Method.CASH
        try:
            ret = record_return(sale, lines, request.user, reason=reason, refund_method=method)
        except ValueError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Return {ret.receipt_no} recorded — refund ₱{ret.refund_amount:.2f}.")
            return redirect("return_receipt", pk=ret.pk)
    context = {
        "sale": sale,
        "items": sale.items.select_related("product"),
        "methods": Return.Method.choices,
        "has_returnable": any(i.returnable_quantity for i in sale.items.all()),
    }
    return render(request, "pos/return_form.html", context)


@manager_required
def return_receipt(request, pk):
    ret = get_object_or_404(
        Return.objects.select_related("sale", "processed_by").prefetch_related("items__product"), pk=pk
    )
    return render(request, "pos/return_receipt.html", {"ret": ret})


@manager_required
def sales_list(request):
    sales = (
        Sale.objects.select_related("cashier")
        .prefetch_related("items__product")
        .annotate(refunded=Sum("returns__refund_amount"), return_count=Count("returns"))
    )
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
    total_refunded = sum((s.refunded or 0) for s in sales)
    context = {
        "sales": sales,
        "total": total,
        "total_refunded": total_refunded,
        "net_total": total - total_refunded,
        "start": start,
        "end": end,
        "filter_active": bool(start or end),
        "filter_error": error,
    }
    return render(request, "pos/sales_list.html", context)


@manager_required
def sales_report(request):
    raw_days = request.GET.get("days", "1").strip() or "1"
    invalid_days = False
    try:
        days = int(raw_days)
        if not 1 <= days <= 365:
            raise ValueError
    except ValueError:
        days = 1
        invalid_days = True

    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    sales = (
        Sale.objects.select_related("cashier")
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .order_by("-created_at")
    )
    summary = sales.aggregate(
        total=Sum("total"),
        subtotal=Sum("subtotal"),
        discount=Sum("discount"),
        count=Count("id"),
    )
    returns = Return.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    refund_summary = returns.aggregate(total=Sum("refund_amount"), count=Count("id"))
    refund_total = refund_summary["total"] or Decimal("0")
    net_sales = (summary["total"] or Decimal("0")) - refund_total
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
            "days": days,
            "invalid_days": invalid_days,
            "start": start,
            "end": end,
        "summary": summary,
            "refund_summary": refund_summary,
            "refund_total": refund_total,
            "net_sales": net_sales,
            "returns": returns,
            "daily_sales": daily_sales,
            "sales": sales,
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


def _parse_days(request):
    raw = request.GET.get("days", "30").strip() or "30"
    try:
        days = int(raw)
        if not 1 <= days <= 365:
            raise ValueError
        return days, False
    except ValueError:
        return 30, True


def build_analytics(days):
    """Aggregate sales, cost, and returns for the last `days` days (inclusive)."""
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    items = SaleItem.objects.filter(
        sale__created_at__date__gte=start, sale__created_at__date__lte=end
    )
    cost_expr = Sum(F("quantity") * F("product__cost_price"))

    sales = Sale.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    sales_sum = sales.aggregate(gross=Sum("subtotal"), discount=Sum("discount"), total=Sum("total"), count=Count("id"))
    returns = Return.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    refunds = returns.aggregate(total=Sum("refund_amount"), count=Count("id"))

    line_revenue = items.aggregate(v=Sum("subtotal"))["v"] or Decimal("0")
    cogs = items.aggregate(v=cost_expr)["v"] or Decimal("0")
    units = items.aggregate(v=Sum("quantity"))["v"] or 0
    refund_total = refunds["total"] or Decimal("0")
    net_sales = (sales_sum["total"] or Decimal("0")) - refund_total
    gross_profit = net_sales - cogs
    margin = (gross_profit / net_sales * 100) if net_sales else Decimal("0")
    txns = sales_sum["count"] or 0

    top_products = [
        {
            "name": row["product__name"],
            "units": row["units"],
            "revenue": float(row["revenue"] or 0),
            "profit": float((row["revenue"] or 0) - (row["cost"] or 0)),
        }
        for row in items.values("product__name")
        .annotate(units=Sum("quantity"), revenue=Sum("subtotal"), cost=cost_expr)
        .order_by("-revenue")[:10]
    ]

    category_rows = (
        items.values("product__category__name")
        .annotate(revenue=Sum("subtotal"), units=Sum("quantity"))
        .order_by("-revenue")
    )
    categories = [
        {
            "name": row["product__category__name"] or "Uncategorized",
            "revenue": float(row["revenue"] or 0),
            "units": row["units"],
        }
        for row in category_rows
    ]

    daily_refunds = {
        row["day"]: row["refund"] or 0
        for row in returns.extra({"day": "date(created_at)"}).values("day").annotate(refund=Sum("refund_amount"))
    }
    daily = []
    for row in (
        sales.extra({"day": "date(created_at)"})
        .values("day")
        .annotate(total=Sum("total"), count=Count("id"))
        .order_by("day")
    ):
        refund = daily_refunds.get(row["day"], 0)
        daily.append(
            {
                "day": str(row["day"]),
                "sales": float(row["total"] or 0),
                "refund": float(refund or 0),
                "net": float((row["total"] or 0) - (refund or 0)),
            }
        )

    return {
        "days": days,
        "start": str(start),
        "end": str(end),
        "kpis": {
            "gross_sales": float(sales_sum["gross"] or 0),
            "discounts": float(sales_sum["discount"] or 0),
            "refunds": float(refund_total),
            "net_sales": float(net_sales),
            "cogs": float(cogs),
            "gross_profit": float(gross_profit),
            "margin": float(margin),
            "transactions": txns,
            "units_sold": units,
            "avg_sale": float((sales_sum["total"] or 0) / txns) if txns else 0,
            "refund_count": refunds["count"] or 0,
            "line_revenue": float(line_revenue),
        },
        "daily": daily,
        "top_products": top_products,
        "categories": categories,
    }


@manager_required
def analytics_report(request):
    days, invalid_days = _parse_days(request)
    return render(
        request,
        "reports/analytics_report.html",
        {"days": days, "invalid_days": invalid_days},
    )


@manager_required
def analytics_data(request):
    days, _ = _parse_days(request)
    return JsonResponse(build_analytics(days))


@manager_required
def analytics_export(request):
    days, _ = _parse_days(request)
    data = build_analytics(days)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="alvanz-analytics-{data["start"]}-to-{data["end"]}.csv"'
    writer = csv.writer(response)
    writer.writerow(["AlvanzStock Analytics", f"{data['start']} to {data['end']}"])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    for key, value in data["kpis"].items():
        writer.writerow([key.replace("_", " ").title(), value])
    writer.writerow([])
    writer.writerow(["Product", "Units", "Revenue", "Profit"])
    for row in data["top_products"]:
        writer.writerow([row["name"], row["units"], row["revenue"], row["profit"]])
    writer.writerow([])
    writer.writerow(["Category", "Units", "Revenue"])
    for row in data["categories"]:
        writer.writerow([row["name"], row["units"], row["revenue"]])
    return response