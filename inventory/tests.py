from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, Product


class RealTimeStockTests(TestCase):
	def setUp(self):
		user = get_user_model().objects.create_user(username="stock-viewer", password="test-pass")
		self.client.force_login(user)
		category = Category.objects.create(name="Tools")
		self.product = Product.objects.create(
			name="Hammer",
			sku="HAM-001",
			category=category,
			quantity=8,
			min_stock_level=10,
		)

	def test_stock_page_renders(self):
		response = self.client.get("/real-time-stock/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Live stock")

	def test_stock_movement_form_has_back_link(self):
		response = self.client.get("/stock/new/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Back to Stock")

	def test_stock_data_returns_current_product_quantities(self):
		response = self.client.get("/real-time-stock/data/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["products"][0]["quantity"], 8)
		self.assertTrue(response.json()["products"][0]["is_low_stock"])

	def test_stock_data_reflects_quantity_changes(self):
		self.product.quantity = 14
		self.product.save(update_fields=["quantity"])

		response = self.client.get("/real-time-stock/data/")

		self.assertEqual(response.json()["products"][0]["quantity"], 14)
		self.assertFalse(response.json()["products"][0]["is_low_stock"])


class ProductImageUploadTests(TestCase):
	def setUp(self):
		user = get_user_model().objects.create_user(username="image-uploader", password="test-pass")
		self.client.force_login(user)
		media_directory = TemporaryDirectory()
		self.addCleanup(media_directory.cleanup)
		media_settings = override_settings(MEDIA_ROOT=media_directory.name)
		media_settings.enable()
		self.addCleanup(media_settings.disable)

	def test_uploaded_product_image_is_saved_and_displayed_in_pos(self):
		image_content = BytesIO()
		Image.new("RGB", (2, 2), color="red").save(image_content, format="PNG")
		image = SimpleUploadedFile("hammer.png", image_content.getvalue(), content_type="image/png")
		response = self.client.post(
			reverse("product_create"),
			{
				"name": "Image Hammer",
				"sku": "IMG-HAM-001",
				"image": image,
				"unit": "pcs",
				"cost_price": "10.00",
				"sell_price": "15.00",
				"min_stock_level": "2",
				"is_active": "on",
			},
		)

		self.assertRedirects(response, reverse("product_list"))
		product = Product.objects.get(sku="IMG-HAM-001")
		self.assertTrue(product.image.name.startswith("products/"))

		pos_response = self.client.get(reverse("pos_screen"))
		self.assertContains(pos_response, product.image.url)
