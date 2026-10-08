from django.contrib.auth import get_user_model
from django.test import TestCase


# Verifies Stock Viewer middleware and the navigation rendered by the live-stock template.
class StockViewerAccessTests(TestCase):
	def setUp(self):
		user = get_user_model().objects.create_user(
			username="stock-only",
			password="test-pass",
			role=get_user_model().Role.STOCK_VIEWER,
		)
		self.client.force_login(user)

	def test_stock_viewer_can_open_live_stock(self):
		response = self.client.get("/real-time-stock/")
		data_response = self.client.get("/real-time-stock/data/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Live Stock")
		self.assertEqual(data_response.status_code, 200)

	def test_stock_viewer_is_redirected_from_other_pages(self):
		for path in ("/", "/products/", "/pos/", "/sales/"):
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertRedirects(response, "/real-time-stock/", fetch_redirect_response=False)

	def test_stock_viewer_navigation_only_shows_live_stock(self):
		response = self.client.get("/real-time-stock/")

		self.assertContains(response, "Live Stock")
		self.assertNotContains(response, "Dashboard")
		self.assertNotContains(response, "Point of Sale")
