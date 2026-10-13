from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Product
from .realtime import STOCK_GROUP, serialize_product


# Streams live stock to authenticated clients and relays per-product update broadcasts.
class StockConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(STOCK_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({"type": "snapshot", "products": await self.get_products()})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(STOCK_GROUP, self.channel_name)

    async def stock_update(self, event):
        await self.send_json({"type": "product", "product": event["product"]})

    async def notify(self, event):
        await self.send_json({"type": event["event"]})

    @database_sync_to_async
    def get_products(self):
        products = Product.objects.filter(is_active=True).select_related("category").order_by("name")
        return [serialize_product(product) for product in products]
