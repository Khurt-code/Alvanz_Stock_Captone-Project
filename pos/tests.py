from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Sale


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
