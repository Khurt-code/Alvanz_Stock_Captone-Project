from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .consumers import StockConsumer
from .models import Category, Product, StockTransaction


# Exercises inventory routes and checks product-image uploads render through the POS product data.
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
		self.assertContains(pos_response, f'data-image="{product.image.url}"')


# Verifies the real-time WebSocket consumer streams stock and relays broadcast updates.
class StockWebSocketTests(TransactionTestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="ws-user", password="test-pass")
		self.category = Category.objects.create(name="Tools")
		self.product = Product.objects.create(
			name="Hammer",
			sku="HAM-WS",
			category=self.category,
			quantity=5,
			min_stock_level=2,
		)

	async def _connect(self, user):
		communicator = WebsocketCommunicator(StockConsumer.as_asgi(), "/ws/stock/")
		communicator.scope["user"] = user
		connected, _ = await communicator.connect()
		return communicator, connected

	async def test_authenticated_client_receives_snapshot(self):
		communicator, connected = await self._connect(self.user)

		self.assertTrue(connected)
		message = await communicator.receive_json_from()
		self.assertEqual(message["type"], "snapshot")
		self.assertEqual(message["products"][0]["sku"], "HAM-WS")
		await communicator.disconnect()

	async def test_anonymous_client_is_rejected(self):
		communicator, connected = await self._connect(AnonymousUser())

		self.assertFalse(connected)

	async def test_group_broadcast_is_relayed_to_client(self):
		communicator, connected = await self._connect(self.user)
		await communicator.receive_json_from()  # consume snapshot

		product = {"id": self.product.id, "name": "Hammer", "quantity": 15}
		await get_channel_layer().group_send("stock_updates", {"type": "stock.update", "product": product})

		message = await communicator.receive_json_from()
		self.assertEqual(message["type"], "product")
		self.assertEqual(message["product"]["quantity"], 15)
		await communicator.disconnect()


# Verifies stock changes trigger the broadcast that feeds the WebSocket clients.
class StockBroadcastTests(TestCase):
	def setUp(self):
		self.product = Product.objects.create(name="Nail", sku="NAIL-1", quantity=5, min_stock_level=2)

	def test_stock_transaction_broadcasts_new_quantity(self):
		with patch("inventory.models.broadcast_stock_update") as broadcast:
			StockTransaction.objects.create(
				product=self.product, transaction_type=StockTransaction.Type.STOCK_IN, quantity=10
			)

		broadcast.assert_called_once()
		self.assertEqual(broadcast.call_args[0][0].quantity, 15)

	def test_deleting_transaction_broadcasts_reversed_quantity(self):
		txn = StockTransaction.objects.create(
			product=self.product, transaction_type=StockTransaction.Type.STOCK_IN, quantity=10
		)
		self.product.refresh_from_db()

		with patch("inventory.models.broadcast_stock_update") as broadcast:
			txn.delete()

		broadcast.assert_called_once()
		self.assertEqual(broadcast.call_args[0][0].quantity, 5)
