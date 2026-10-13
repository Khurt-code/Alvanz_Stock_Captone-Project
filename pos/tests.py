from datetime import datetime, time, timedelta
from decimal import Decimal
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import Product

from .models import Return, Sale, record_return, record_sale

from pos.views import build_analytics


# Verifies manager sales-report views filter Sale records and pass printable report data to templates.
class SalesReportTests(TestCase):
	def setUp(self):
		self.manager = get_user_model().objects.create_user(
			username="report-manager",
			password="test-pass",
			role=get_user_model().Role.MANAGER,
		)
		self.client.force_login(self.manager)

	def create_sale(self, days_ago, amount):
		sale = Sale.objects.create(
			cashier=self.manager,
			subtotal=Decimal(amount),
			total=Decimal(amount),
		)
		sale_date = timezone.localdate() - timedelta(days=days_ago)
		created_at = timezone.make_aware(datetime.combine(sale_date, time(12)))
		Sale.objects.filter(pk=sale.pk).update(created_at=created_at)
		return sale

	def test_report_defaults_to_today_and_has_print_control(self):
		self.create_sale(0, "25.00")
		self.create_sale(1, "40.00")

		response = self.client.get(reverse("sales_report"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["days"], 1)
		self.assertEqual(response.context["summary"]["count"], 1)
		self.assertContains(response, "Print Report")

	def test_custom_day_range_includes_boundary_day_and_excludes_older_sales(self):
		self.create_sale(0, "25.00")
		self.create_sale(2, "40.00")
		self.create_sale(3, "60.00")

		response = self.client.get(reverse("sales_report"), {"days": "3"})

		self.assertEqual(response.context["summary"]["count"], 2)
		self.assertEqual(len(response.context["sales"]), 2)
		self.assertEqual(response.context["start"], timezone.localdate() - timedelta(days=2))

	def test_invalid_day_count_falls_back_to_today(self):
		response = self.client.get(reverse("sales_report"), {"days": "500"})

		self.assertEqual(response.context["days"], 1)
		self.assertTrue(response.context["invalid_days"])


# Verifies the return workflow restocks inventory, refunds proportionally, and blocks over-returning.
class ReturnTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.manager = User.objects.create_user(
			username="return-manager", password="test-pass", role=User.Role.MANAGER
		)
		self.cashier = User.objects.create_user(
			username="return-cashier", password="test-pass", role=User.Role.CASHIER
		)
		self.product = Product.objects.create(
			name="Cement", sku="CEM-1", sell_price=Decimal("100.00"), cost_price=Decimal("80.00"), quantity=10
		)

	def make_sale(self, qty=2, discount=0):
		return record_sale(
			[(self.product, qty)], self.cashier, cash_tendered=Decimal("500.00"), discount=Decimal(discount)
		)

	def test_full_return_restocks_and_records_refund(self):
		sale = self.make_sale()
		self.assertEqual(self.product.quantity, 8)

		ret = record_return(sale, [(sale.items.first(), 2, True)], self.manager)

		self.product.refresh_from_db()
		self.assertEqual(self.product.quantity, 10)
		self.assertEqual(ret.refund_amount, Decimal("200.00"))
		self.assertEqual(ret.items.count(), 1)
		self.assertTrue(ret.items.first().restock)
		self.assertTrue(Return.objects.filter(pk=ret.pk).exists())

	def test_discount_is_refunded_proportionally(self):
		sale = self.make_sale(discount="20.00")

		ret = record_return(sale, [(sale.items.first(), 2, True)], self.manager)

		self.assertEqual(ret.refund_amount, Decimal("180.00"))

	def test_partial_return_refunds_only_returned_units(self):
		sale = self.make_sale(qty=2)

		ret = record_return(sale, [(sale.items.first(), 1, True)], self.manager)

		self.assertEqual(ret.refund_amount, Decimal("100.00"))
		self.assertEqual(ret.items.first().subtotal, Decimal("100.00"))

	def test_over_return_is_rejected(self):
		sale = self.make_sale()
		with self.assertRaises(ValueError):
			record_return(sale, [(sale.items.first(), 3, True)], self.manager)

	def test_partial_then_full_return_limits_remaining(self):
		sale = self.make_sale()
		item = sale.items.first()

		record_return(sale, [(item, 1, True)], self.manager)
		self.assertEqual(item.returnable_quantity, 1)

		record_return(sale, [(item, 1, True)], self.manager)
		self.assertEqual(item.returnable_quantity, 0)

		with self.assertRaises(ValueError):
			record_return(sale, [(item, 1, True)], self.manager)

	def test_non_restock_return_does_not_change_stock(self):
		sale = self.make_sale()
		self.assertEqual(self.product.quantity, 8)

		record_return(sale, [(sale.items.first(), 2, False)], self.manager)

		self.product.refresh_from_db()
		self.assertEqual(self.product.quantity, 8)

	def test_cashier_cannot_access_return_view(self):
		sale = self.make_sale()
		self.client.force_login(self.cashier)

		response = self.client.get(reverse("sale_return", args=[sale.pk]))

		self.assertEqual(response.status_code, 302)

	def test_manager_can_process_return_through_view(self):
		sale = self.make_sale()
		item = sale.items.first()
		self.client.force_login(self.manager)

		form = self.client.get(reverse("sale_return", args=[sale.pk]))
		self.assertEqual(form.status_code, 200)
		self.assertContains(form, "Process Return")

		response = self.client.post(
			reverse("sale_return", args=[sale.pk]),
			{f"qty_{item.id}": "2", f"restock_{item.id}": "on", "refund_method": "cash"},
		)

		self.assertEqual(response.status_code, 302)
		self.product.refresh_from_db()
		self.assertEqual(self.product.quantity, 10)
		self.assertEqual(Return.objects.count(), 1)

	def test_sales_report_net_reflects_refunds(self):
		sale = self.make_sale()
		record_return(sale, [(sale.items.first(), 2, True)], self.manager)
		self.client.force_login(self.manager)

		response = self.client.get(reverse("sales_report"))

		self.assertEqual(response.context["refund_total"], Decimal("200.00"))
		self.assertEqual(response.context["net_sales"], Decimal("0.00"))


# Verifies the manager-only analytics dashboard, its JSON feed, CSV export, and live sale broadcasts.
class AnalyticsTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.manager = User.objects.create_user(
			username="analytics-manager", password="test-pass", role=User.Role.MANAGER
		)
		self.cashier = User.objects.create_user(
			username="analytics-cashier", password="test-pass", role=User.Role.CASHIER
		)
		self.product = Product.objects.create(
			name="Bolt", sku="BOLT-1", sell_price=Decimal("50.00"), cost_price=Decimal("30.00"), quantity=50
		)

	def make_sale(self, qty=2, discount=0):
		return record_sale(
			[(self.product, qty)], self.cashier, cash_tendered=Decimal("1000.00"), discount=Decimal(discount)
		)

	def test_analytics_page_is_manager_only(self):
		self.client.force_login(self.cashier)
		self.assertEqual(self.client.get(reverse("analytics_report")).status_code, 302)

		self.client.force_login(self.manager)
		response = self.client.get(reverse("analytics_report"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Export CSV")

	def test_data_endpoint_reports_profit_and_units(self):
		self.make_sale(qty=2)
		self.make_sale(qty=2)
		self.client.force_login(self.manager)

		data = self.client.get(reverse("analytics_data")).json()

		self.assertEqual(data["kpis"]["units_sold"], 4)
		self.assertEqual(data["kpis"]["gross_sales"], 200.0)
		self.assertEqual(data["kpis"]["cogs"], 120.0)
		self.assertEqual(data["kpis"]["gross_profit"], 80.0)
		self.assertEqual(data["kpis"]["margin"], 40.0)
		self.assertEqual(data["kpis"]["transactions"], 2)
		self.assertEqual(data["top_products"][0]["profit"], 80.0)
		self.assertEqual(len(data["daily"]), 1)

	def test_data_nets_out_refunds(self):
		sale = self.make_sale(qty=2)
		record_return(sale, [(sale.items.first(), 2, True)], self.manager)
		self.client.force_login(self.manager)

		data = self.client.get(reverse("analytics_data")).json()

		self.assertEqual(data["kpis"]["refunds"], 100.0)
		self.assertEqual(data["kpis"]["net_sales"], 0.0)

	def test_csv_export_content(self):
		self.make_sale(qty=2)
		self.client.force_login(self.manager)

		response = self.client.get(reverse("analytics_export"))

		self.assertEqual(response.status_code, 200)
		self.assertIn("text/csv", response["Content-Type"])
		self.assertIn("attachment", response["Content-Disposition"])
		body = response.content.decode()
		self.assertIn("AlvanzStock Analytics", body)
		self.assertIn("Bolt", body)

	def test_date_range_excludes_older_sales(self):
		sale = self.make_sale(qty=2)
		old = timezone.make_aware(datetime.combine(timezone.localdate() - timedelta(days=10), time(12)))
		Sale.objects.filter(pk=sale.pk).update(created_at=old)
		self.client.force_login(self.manager)

		recent = build_analytics(1)
		older = build_analytics(30)

		self.assertEqual(recent["kpis"]["units_sold"], 0)
		self.assertEqual(older["kpis"]["units_sold"], 2)

	def test_recording_a_sale_broadcasts_event_after_commit(self):
		with patch("inventory.realtime.broadcast_event") as broadcast:
			with self.captureOnCommitCallbacks(execute=True):
				self.make_sale(qty=1)

		broadcast.assert_called_once_with("sale")


# Verifies a cashier keeps full POS access (checkout, receipt) while inventory writes stay manager-only.
class CashierPosTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.cashier = User.objects.create_user(
			username="pos-cashier", password="test-pass", role=User.Role.CASHIER
		)
		self.product = Product.objects.create(
			name="Paint", sku="PNT-1", sell_price=Decimal("100.00"), cost_price=Decimal("60.00"), quantity=5
		)
		self.client.force_login(self.cashier)

	def test_cashier_can_open_pos_screen(self):
		response = self.client.get(reverse("pos_screen"))

		self.assertEqual(response.status_code, 200)

	def test_cashier_can_checkout_and_view_receipt(self):
		response = self.client.post(
			reverse("pos_checkout"),
			data=json.dumps({"items": [{"id": self.product.id, "qty": 2}], "cash": "200", "discount": "0"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()["success"])
		sale = Sale.objects.get(pk=response.json()["sale_id"])
		self.product.refresh_from_db()
		self.assertEqual(self.product.quantity, 3)

		receipt = self.client.get(reverse("sale_receipt", args=[sale.pk]))
		self.assertEqual(receipt.status_code, 200)
